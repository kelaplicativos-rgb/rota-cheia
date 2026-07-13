package br.com.rotaai.avaliador;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.webkit.CookieManager;
import android.webkit.JavascriptInterface;
import android.webkit.SafeBrowsingResponse;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.TextView;
import android.widget.Toast;

import org.json.JSONObject;
import org.json.JSONTokener;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;
import java.util.zip.GZIPInputStream;

public final class MainActivity extends Activity {
    private static final String HOME_URL = "https://www.blablacar.com.br/rides";
    private static final String STATE_KEY = "webview_state";
    private static final String LOG_FILE_NAME = "rotaai-debug-current.jsonl";
    private static final long MAX_LOG_BYTES = 4L * 1024L * 1024L;
    private static final int EXPORT_LOG_REQUEST = 9051;

    private WebView webView;
    private ProgressBar progressBar;
    private TextView statusView;
    private String injectionScript;
    private String pendingExportText = "";
    private final Handler handler = new Handler(Looper.getMainLooper());
    private int lastProgressBucket = -1;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        appendNativeLog("lifecycle", "activity_create", "version=0.5.0");
        injectionScript = loadAsset("generator.js") + "\n"
                + loadAsset("rotaai-part1.js") + "\n"
                + loadAsset("rotaai-part2.js") + "\n"
                + loadAsset("rotaai-part3.js") + "\n"
                + loadAsset("rotaai-part4.js") + "\n"
                + loadAsset("rotaai-part5-debug.js");
        buildUi();
        configureWebView();

        if (savedInstanceState != null && savedInstanceState.containsKey(STATE_KEY)) {
            appendNativeLog("lifecycle", "webview_restore", "restoring saved state");
            webView.restoreState(savedInstanceState.getBundle(STATE_KEY));
        } else {
            showFirstUseNotice();
            webView.loadUrl(HOME_URL);
        }
    }

    private void buildUi() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(Color.WHITE);
        getWindow().setStatusBarColor(Color.rgb(0, 90, 90));
        getWindow().setNavigationBarColor(Color.WHITE);

        LinearLayout toolbar = new LinearLayout(this);
        toolbar.setOrientation(LinearLayout.HORIZONTAL);
        toolbar.setGravity(Gravity.CENTER_VERTICAL);
        toolbar.setPadding(dp(8), dp(4), dp(8), dp(4));
        toolbar.setBackgroundColor(Color.rgb(0, 106, 106));

        TextView title = new TextView(this);
        title.setText("RotaAi 0.5");
        title.setTextColor(Color.WHITE);
        title.setTextSize(18);
        title.setTypeface(null, android.graphics.Typeface.BOLD);
        toolbar.addView(title, new LinearLayout.LayoutParams(0, dp(48), 1f));

        Button back = toolbarButton("Voltar");
        back.setOnClickListener(v -> {
            appendNativeLog("user", "toolbar_back", sanitizedCurrentUrl());
            if (webView.canGoBack()) webView.goBack();
        });
        toolbar.addView(back);

        Button home = toolbarButton("Viagens");
        home.setOnClickListener(v -> {
            appendNativeLog("user", "toolbar_trips", HOME_URL);
            webView.loadUrl(HOME_URL);
        });
        toolbar.addView(home);

        LinearLayout actionRow = new LinearLayout(this);
        actionRow.setOrientation(LinearLayout.HORIZONTAL);
        actionRow.setPadding(dp(5), dp(4), dp(5), dp(3));
        actionRow.setBackgroundColor(Color.rgb(236, 247, 247));

        Button review = actionButton("Revisar pendentes", Color.rgb(0, 106, 106));
        review.setOnClickListener(v -> callAutomation(
                "review_pending",
                "window.RotaAiDebug&&window.RotaAiDebug.clearStop&&window.RotaAiDebug.clearStop('botão Revisar pendentes');"
                        + "window.RotaAiAndroid&&window.RotaAiAndroid.startSmartReview&&window.RotaAiAndroid.startSmartReview();"));
        actionRow.addView(review, weightedButtonParams(1.5f));

        Button approve = actionButton("Aprovar/próxima", Color.rgb(33, 113, 70));
        approve.setOnClickListener(v -> callAutomation(
                "approve_next",
                "window.RotaAiAndroid&&window.RotaAiAndroid.moveReviewNext&&window.RotaAiAndroid.moveReviewNext(true);"));
        actionRow.addView(approve, weightedButtonParams(1.2f));

        Button publish = actionButton("Publicar", Color.rgb(35, 83, 145));
        publish.setOnClickListener(v -> callAutomation(
                "publish_approved",
                "window.RotaAiAndroid&&window.RotaAiAndroid.startPublish&&window.RotaAiAndroid.startPublish();"));
        actionRow.addView(publish, weightedButtonParams(0.9f));

        LinearLayout debugRow = new LinearLayout(this);
        debugRow.setOrientation(LinearLayout.HORIZONTAL);
        debugRow.setPadding(dp(5), dp(3), dp(5), dp(4));
        debugRow.setBackgroundColor(Color.rgb(236, 247, 247));

        Button stop = actionButton("STOP", Color.rgb(177, 38, 38));
        stop.setTypeface(null, android.graphics.Typeface.BOLD);
        stop.setOnClickListener(v -> stopAutomation());
        debugRow.addView(stop, weightedButtonParams(1f));

        Button export = actionButton("Exportar log", Color.rgb(74, 74, 74));
        export.setOnClickListener(v -> requestExportLog());
        debugRow.addView(export, weightedButtonParams(1f));

        statusView = new TextView(this);
        statusView.setText("Faça login e toque em Revisar pendentes.");
        statusView.setTextColor(Color.rgb(30, 65, 65));
        statusView.setTextSize(12);
        statusView.setPadding(dp(10), dp(5), dp(10), dp(5));
        statusView.setBackgroundColor(Color.rgb(222, 241, 240));

        progressBar = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
        progressBar.setMax(100);
        progressBar.setProgress(0);
        progressBar.setVisibility(View.GONE);

        webView = new WebView(this);
        root.addView(toolbar, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(56)));
        root.addView(actionRow, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(52)));
        root.addView(debugRow, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(46)));
        root.addView(statusView, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        root.addView(progressBar, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(3)));
        root.addView(webView, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f));
        setContentView(root);
    }

    private LinearLayout.LayoutParams weightedButtonParams(float weight) {
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.MATCH_PARENT, weight);
        params.setMargins(dp(2), 0, dp(2), 0);
        return params;
    }

    private Button toolbarButton(String text) {
        Button button = new Button(this);
        button.setText(text);
        button.setTextSize(11);
        button.setAllCaps(false);
        button.setTextColor(Color.WHITE);
        button.setBackgroundColor(Color.TRANSPARENT);
        button.setPadding(dp(5), 0, dp(5), 0);
        button.setMinWidth(0);
        button.setMinimumWidth(0);
        button.setMinHeight(0);
        button.setMinimumHeight(0);
        return button;
    }

    private Button actionButton(String text, int backgroundColor) {
        Button button = new Button(this);
        button.setText(text);
        button.setTextSize(11);
        button.setAllCaps(false);
        button.setTextColor(Color.WHITE);
        button.setBackgroundColor(backgroundColor);
        button.setPadding(dp(4), 0, dp(4), 0);
        button.setMinWidth(0);
        button.setMinimumWidth(0);
        button.setMinHeight(0);
        button.setMinimumHeight(0);
        return button;
    }

    @SuppressLint({"SetJavaScriptEnabled", "JavascriptInterface"})
    private void configureWebView() {
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setDatabaseEnabled(true);
        settings.setAllowFileAccess(false);
        settings.setAllowContentAccess(false);
        settings.setAllowFileAccessFromFileURLs(false);
        settings.setAllowUniversalAccessFromFileURLs(false);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        settings.setSupportMultipleWindows(false);
        settings.setJavaScriptCanOpenWindowsAutomatically(false);
        settings.setBuiltInZoomControls(false);
        settings.setDisplayZoomControls(false);
        settings.setLoadWithOverviewMode(true);
        settings.setUseWideViewPort(true);
        settings.setMediaPlaybackRequiresUserGesture(true);
        settings.setUserAgentString(settings.getUserAgentString() + " RotaAiAvaliador/0.5.0");
        if (android.os.Build.VERSION.SDK_INT >= 26) settings.setSafeBrowsingEnabled(true);

        CookieManager cookieManager = CookieManager.getInstance();
        cookieManager.setAcceptCookie(true);
        cookieManager.setAcceptThirdPartyCookies(webView, true);

        webView.addJavascriptInterface(new NativeBridge(), "RotaAiNative");
        WebView.setWebContentsDebuggingEnabled(false);
        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onProgressChanged(WebView view, int newProgress) {
                progressBar.setProgress(newProgress);
                progressBar.setVisibility(newProgress >= 100 ? View.GONE : View.VISIBLE);
                int bucket = newProgress / 25;
                if (bucket != lastProgressBucket) {
                    lastProgressBucket = bucket;
                    appendNativeLog("page", "progress", "progress=" + newProgress + " url=" + sanitizedCurrentUrl());
                }
            }

            @Override
            public void onReceivedTitle(WebView view, String title) {
                appendNativeLog("page", "title", safeDetail(title));
            }
        });

        webView.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri uri = request.getUrl();
                appendNativeLog("navigation", "request", sanitizeUri(uri));
                if (isAllowedUri(uri)) return false;
                openExternally(uri);
                return true;
            }

            @Override
            public boolean shouldOverrideUrlLoading(WebView view, String url) {
                Uri uri = Uri.parse(url);
                appendNativeLog("navigation", "request_legacy", sanitizeUri(uri));
                if (isAllowedUri(uri)) return false;
                openExternally(uri);
                return true;
            }

            @Override
            public void onPageStarted(WebView view, String url, android.graphics.Bitmap favicon) {
                appendNativeLog("page", "started", sanitizeUrl(url));
                updateStatus("Carregando página...");
                super.onPageStarted(view, url, favicon);
            }

            @Override
            public void onPageFinished(WebView view, String url) {
                super.onPageFinished(view, url);
                appendNativeLog("page", "finished", sanitizeUrl(url));
                injectIfAllowed(url, "page_finished");
                handler.postDelayed(() -> injectIfAllowed(webView.getUrl(), "delayed_500ms"), 500);
                handler.postDelayed(() -> injectIfAllowed(webView.getUrl(), "delayed_1400ms"), 1400);
            }

            @Override
            public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                if (request.isForMainFrame()) {
                    appendNativeLog("error", "web_error", "code=" + error.getErrorCode()
                            + " description=" + safeDetail(error.getDescription())
                            + " url=" + sanitizeUri(request.getUrl()));
                    updateStatus("Erro ao carregar a página. Exporte o log.");
                }
                super.onReceivedError(view, request, error);
            }

            @Override
            public void onSafeBrowsingHit(WebView view, WebResourceRequest request, int threatType,
                                          SafeBrowsingResponse callback) {
                appendNativeLog("security", "safe_browsing_block", "type=" + threatType + " url=" + sanitizeUri(request.getUrl()));
                callback.backToSafety(true);
                updateStatus("Navegação bloqueada pelo Safe Browsing.");
            }

            @Override
            public void onReceivedHttpError(WebView view, WebResourceRequest request,
                                            WebResourceResponse errorResponse) {
                if (request.isForMainFrame()) {
                    appendNativeLog("error", "http_error", "status=" + errorResponse.getStatusCode()
                            + " url=" + sanitizeUri(request.getUrl()));
                    updateStatus("A página retornou erro " + errorResponse.getStatusCode() + ".");
                }
            }
        });
    }

    private final class NativeBridge {
        @JavascriptInterface
        public void status(String message) {
            String safe = safeDetail(message);
            appendNativeLog("javascript", "status", safe);
            runOnUiThread(() -> updateStatus(safe));
        }

        @JavascriptInterface
        public void log(String eventJson) {
            appendJavascriptLog(eventJson);
        }
    }

    private void callAutomation(String action, String javascript) {
        appendNativeLog("user", action, sanitizedCurrentUrl());
        updateStatus("Executando: " + action.replace('_', ' ') + "...");
        webView.evaluateJavascript(javascript, result ->
                appendNativeLog("javascript", action + "_result", safeDetail(result)));
    }

    private void stopAutomation() {
        appendNativeLog("user", "stop_button", sanitizedCurrentUrl());
        updateStatus("STOP acionado. Interrompendo automação...");
        webView.stopLoading();
        webView.evaluateJavascript(
                "window.RotaAiAndroid&&window.RotaAiAndroid.stopAll"
                        + "?window.RotaAiAndroid.stopAll('STOP nativo acionado pelo usuário')"
                        + ":(window.RotaAiDebug&&window.RotaAiDebug.stopAll"
                        + "?window.RotaAiDebug.stopAll('STOP nativo acionado pelo usuário'):false);",
                result -> appendNativeLog("control", "stop_result", safeDetail(result)));
    }

    private void requestExportLog() {
        appendNativeLog("user", "export_log_button", sanitizedCurrentUrl());
        updateStatus("Preparando relatório de debug...");
        String script = "window.RotaAiAndroid&&window.RotaAiAndroid.exportDebugLog"
                + "?window.RotaAiAndroid.exportDebugLog()"
                + ":(window.RotaAiDebug&&window.RotaAiDebug.exportDebugLog"
                + "?window.RotaAiDebug.exportDebugLog():'');";
        webView.evaluateJavascript(script, encoded -> {
            String javascriptLog = decodeJavascriptString(encoded);
            String header = "ROTA AI DEBUG COMPLETO\n"
                    + "Versão: 0.5.0\n"
                    + "Data: " + new SimpleDateFormat("dd/MM/yyyy HH:mm:ss", Locale.getDefault()).format(new Date()) + "\n"
                    + "Página: " + sanitizedCurrentUrl() + "\n"
                    + "Observação: senhas, cookies, tokens, e-mails e telefones não são registrados.\n"
                    + "--- LOG NATIVO ---\n";
            pendingExportText = header + readNativeLog() + "\n--- LOG DA AUTOMAÇÃO ---\n" + javascriptLog + "\n";
            Intent intent = new Intent(Intent.ACTION_CREATE_DOCUMENT);
            intent.addCategory(Intent.CATEGORY_OPENABLE);
            intent.setType("text/plain");
            intent.putExtra(Intent.EXTRA_TITLE, "rotaai-debug-"
                    + new SimpleDateFormat("yyyyMMdd-HHmmss", Locale.US).format(new Date()) + ".txt");
            startActivityForResult(intent, EXPORT_LOG_REQUEST);
        });
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode != EXPORT_LOG_REQUEST || resultCode != RESULT_OK || data == null || data.getData() == null) {
            if (requestCode == EXPORT_LOG_REQUEST) {
                appendNativeLog("user", "export_log_cancelled", "no destination selected");
                updateStatus("Exportação do log cancelada.");
            }
            return;
        }
        Uri destination = data.getData();
        try (OutputStream output = getContentResolver().openOutputStream(destination, "wt")) {
            if (output == null) throw new IOException("Destino indisponível.");
            output.write(pendingExportText.getBytes(StandardCharsets.UTF_8));
            output.flush();
            appendNativeLog("user", "export_log_saved", sanitizeUri(destination));
            updateStatus("Log salvo. Anexe o arquivo aqui para análise.");
            Toast.makeText(this, "Log salvo com sucesso.", Toast.LENGTH_LONG).show();
        } catch (IOException error) {
            appendNativeLog("error", "export_log_failed", safeDetail(error.getMessage()));
            updateStatus("Falha ao salvar o log.");
            Toast.makeText(this, "Não foi possível salvar o log.", Toast.LENGTH_LONG).show();
        } finally {
            pendingExportText = "";
        }
    }

    private void injectIfAllowed(String url, String reason) {
        if (url == null || !isAllowedUri(Uri.parse(url)) || injectionScript.isBlank()) {
            appendNativeLog("javascript", "injection_skipped", "reason=" + reason + " url=" + sanitizeUrl(url));
            return;
        }
        appendNativeLog("javascript", "injection_start", "reason=" + reason + " url=" + sanitizeUrl(url));
        webView.evaluateJavascript(injectionScript, value ->
                appendNativeLog("javascript", "injection_done", "reason=" + reason + " result=" + safeDetail(value)));
    }

    private boolean isAllowedUri(Uri uri) {
        if (uri == null || uri.getScheme() == null || uri.getHost() == null) return false;
        if (!"https".equalsIgnoreCase(uri.getScheme())) return false;
        String host = uri.getHost().toLowerCase(Locale.ROOT);
        return host.equals("blablacar.com.br")
                || host.endsWith(".blablacar.com.br")
                || host.equals("blablacar.com")
                || host.endsWith(".blablacar.com");
    }

    private void openExternally(Uri uri) {
        appendNativeLog("navigation", "external", sanitizeUri(uri));
        try {
            startActivity(new Intent(Intent.ACTION_VIEW, uri));
        } catch (Exception error) {
            appendNativeLog("error", "external_open_failed", safeDetail(error.getMessage()));
            Toast.makeText(this, "Não foi possível abrir este link.", Toast.LENGTH_SHORT).show();
        }
    }

    private String loadAsset(String name) {
        try (InputStream input = getAssets().open(name);
             ByteArrayOutputStream output = new ByteArrayOutputStream()) {
            byte[] buffer = new byte[8192];
            int read;
            while ((read = input.read(buffer)) >= 0) output.write(buffer, 0, read);
            String raw = output.toString(StandardCharsets.UTF_8).trim();
            if (raw.startsWith("H4sI")) {
                byte[] compressed = android.util.Base64.decode(raw, android.util.Base64.DEFAULT);
                try (GZIPInputStream gzip = new GZIPInputStream(new ByteArrayInputStream(compressed));
                     ByteArrayOutputStream decoded = new ByteArrayOutputStream()) {
                    while ((read = gzip.read(buffer)) >= 0) decoded.write(buffer, 0, read);
                    return decoded.toString(StandardCharsets.UTF_8);
                }
            }
            return raw;
        } catch (IOException | IllegalArgumentException error) {
            appendNativeLog("error", "asset_load_failed", "asset=" + name + " error=" + safeDetail(error.getMessage()));
            return "console.error('RotaAi: falha ao carregar " + name.replace("'", "") + "');";
        }
    }

    private synchronized void appendNativeLog(String category, String action, String details) {
        try {
            JSONObject event = new JSONObject();
            event.put("ts", new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSSZ", Locale.US).format(new Date()));
            event.put("source", "android");
            event.put("category", safeDetail(category));
            event.put("action", safeDetail(action));
            event.put("details", safeDetail(details));
            appendLogLine(event.toString());
        } catch (Exception ignored) {
            // O sistema de log nunca pode derrubar o aplicativo.
        }
    }

    private synchronized void appendJavascriptLog(String eventJson) {
        if (eventJson == null || eventJson.isBlank()) return;
        String safe = eventJson.length() > 16000 ? eventJson.substring(0, 16000) : eventJson;
        appendLogLine(safe);
    }

    private synchronized void appendLogLine(String line) {
        try {
            File file = getFileStreamPath(LOG_FILE_NAME);
            if (file.exists() && file.length() > MAX_LOG_BYTES) {
                File rotated = getFileStreamPath("rotaai-debug-previous.jsonl");
                if (rotated.exists()) rotated.delete();
                if (!file.renameTo(rotated)) file.delete();
            }
            try (FileOutputStream output = openFileOutput(LOG_FILE_NAME, MODE_APPEND)) {
                output.write((line + "\n").getBytes(StandardCharsets.UTF_8));
            }
        } catch (IOException ignored) {
            // Sem recursão de log em caso de falha no próprio arquivo.
        }
    }

    private String readNativeLog() {
        File file = getFileStreamPath(LOG_FILE_NAME);
        if (!file.exists()) return "Nenhum evento nativo registrado.\n";
        try (FileInputStream input = new FileInputStream(file);
             ByteArrayOutputStream output = new ByteArrayOutputStream()) {
            byte[] buffer = new byte[8192];
            int read;
            while ((read = input.read(buffer)) >= 0) output.write(buffer, 0, read);
            return output.toString(StandardCharsets.UTF_8);
        } catch (IOException error) {
            return "Falha ao ler o log nativo: " + safeDetail(error.getMessage()) + "\n";
        }
    }

    private String decodeJavascriptString(String encoded) {
        if (encoded == null || encoded.equals("null") || encoded.equals("undefined")) return "";
        try {
            Object value = new JSONTokener(encoded).nextValue();
            return value instanceof String ? (String) value : encoded;
        } catch (Exception error) {
            return encoded;
        }
    }

    private String sanitizedCurrentUrl() {
        return sanitizeUrl(webView == null ? "" : webView.getUrl());
    }

    private String sanitizeUrl(String value) {
        if (value == null || value.isBlank()) return "";
        try {
            return sanitizeUri(Uri.parse(value));
        } catch (Exception error) {
            return safeDetail(value);
        }
    }

    private String sanitizeUri(Uri uri) {
        if (uri == null) return "";
        String scheme = uri.getScheme() == null ? "" : uri.getScheme();
        String host = uri.getHost() == null ? "" : uri.getHost();
        String path = uri.getPath() == null ? "" : uri.getPath();
        return safeDetail((scheme.isBlank() ? "" : scheme + "://") + host + path);
    }

    private String safeDetail(Object value) {
        if (value == null) return "";
        String text = value.toString()
                .replaceAll("[\\w.+-]+@[\\w.-]+\\.[A-Za-z]{2,}", "[email]")
                .replaceAll("(?:\\+?55\\s*)?(?:\\(?\\d{2}\\)?\\s*)?\\d{4,5}[-\\s]?\\d{4}", "[telefone]")
                .replaceAll("(?i)(senha|password|token|cookie|authorization)\\s*[:=]\\s*\\S+", "$1=[oculto]")
                .replaceAll("\\s+", " ")
                .trim();
        return text.length() > 1200 ? text.substring(0, 1200) : text;
    }

    private void updateStatus(String message) {
        if (statusView == null) return;
        statusView.setText(message == null || message.isBlank() ? "RotaAi ativo." : message);
    }

    private void showFirstUseNotice() {
        new AlertDialog.Builder(this)
                .setTitle("Automação com diagnóstico")
                .setMessage("Faça login na BlaBlaCar e toque em ‘Revisar pendentes’. "
                        + "O RotaAi registra cada etapa, cada card considerado, o elemento escolhido e os erros. "
                        + "O botão STOP interrompe a automação. Use ‘Exportar log’ para salvar o relatório e anexá-lo no chat. "
                        + "Senhas, cookies e tokens não são registrados.")
                .setPositiveButton("Entendi", null)
                .show();
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }

    @Override
    protected void onSaveInstanceState(Bundle outState) {
        Bundle state = new Bundle();
        webView.saveState(state);
        outState.putBundle(STATE_KEY, state);
        appendNativeLog("lifecycle", "activity_save_state", sanitizedCurrentUrl());
        super.onSaveInstanceState(outState);
    }

    @Override
    public void onBackPressed() {
        appendNativeLog("user", "system_back", sanitizedCurrentUrl());
        if (webView.canGoBack()) webView.goBack();
        else super.onBackPressed();
    }

    @Override
    protected void onDestroy() {
        appendNativeLog("lifecycle", "activity_destroy", sanitizedCurrentUrl());
        handler.removeCallbacksAndMessages(null);
        if (webView != null) {
            webView.stopLoading();
            webView.loadUrl("about:blank");
            webView.clearHistory();
            webView.removeJavascriptInterface("RotaAiNative");
            webView.removeAllViews();
            webView.destroy();
        }
        super.onDestroy();
    }
}
