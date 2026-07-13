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
import android.util.Base64;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.util.Locale;
import java.util.zip.GZIPInputStream;

public final class MainActivity extends Activity {
    private static final String HOME_URL = "https://www.blablacar.com.br/rides";
    private static final String STATE_KEY = "webview_state";

    private WebView webView;
    private ProgressBar progressBar;
    private TextView statusText;
    private String injectionScript;
    private final Handler handler = new Handler(Looper.getMainLooper());

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        injectionScript = loadAsset("generator.js") + "\n"
                + loadAsset("rotaai-part1.js") + "\n"
                + loadAsset("rotaai-part2.js") + "\n"
                + loadAsset("rotaai-part3.js") + "\n"
                + loadAsset("rotaai-part4.js");
        buildUi();
        configureWebView();

        if (savedInstanceState != null && savedInstanceState.containsKey(STATE_KEY)) {
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
        getWindow().setStatusBarColor(Color.rgb(0, 106, 106));
        getWindow().setNavigationBarColor(Color.WHITE);
        root.setOnApplyWindowInsetsListener((view, insets) -> {
            view.setPadding(0, insets.getSystemWindowInsetTop(), 0, insets.getSystemWindowInsetBottom());
            return insets;
        });

        LinearLayout toolbar = new LinearLayout(this);
        toolbar.setOrientation(LinearLayout.HORIZONTAL);
        toolbar.setGravity(Gravity.CENTER_VERTICAL);
        toolbar.setPadding(dp(10), dp(4), dp(8), dp(4));
        toolbar.setBackgroundColor(Color.rgb(0, 106, 106));

        TextView title = new TextView(this);
        title.setText("RotaAi");
        title.setTextColor(Color.WHITE);
        title.setTextSize(19);
        title.setTypeface(null, android.graphics.Typeface.BOLD);
        toolbar.addView(title, new LinearLayout.LayoutParams(0, dp(48), 1f));

        Button back = toolbarButton("Voltar");
        back.setOnClickListener(v -> {
            if (webView.canGoBack()) webView.goBack();
        });
        toolbar.addView(back);

        Button home = toolbarButton("Viagens");
        home.setOnClickListener(v -> webView.loadUrl(HOME_URL));
        toolbar.addView(home);

        progressBar = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
        progressBar.setMax(100);
        progressBar.setProgress(0);
        progressBar.setVisibility(View.GONE);

        statusText = new TextView(this);
        statusText.setText("Entre na conta e toque em Revisar pendentes.");
        statusText.setTextSize(12);
        statusText.setTextColor(Color.rgb(30, 75, 75));
        statusText.setBackgroundColor(Color.rgb(232, 247, 246));
        statusText.setPadding(dp(10), dp(6), dp(10), dp(6));
        statusText.setMaxLines(2);

        webView = new WebView(this);

        LinearLayout bottomBar = new LinearLayout(this);
        bottomBar.setOrientation(LinearLayout.HORIZONTAL);
        bottomBar.setGravity(Gravity.CENTER);
        bottomBar.setPadding(dp(6), dp(6), dp(6), dp(6));
        bottomBar.setBackgroundColor(Color.WHITE);

        Button review = actionButton("Revisar pendentes", true);
        review.setOnClickListener(v -> runCommand("window.RotaAiAndroid.startSmartReview()"));
        bottomBar.addView(review, new LinearLayout.LayoutParams(0, dp(52), 1.25f));

        Button approve = actionButton("Aprovar / próxima", false);
        approve.setOnClickListener(v -> runCommand("window.RotaAiAndroid.moveReviewNext(true)"));
        bottomBar.addView(approve, new LinearLayout.LayoutParams(0, dp(52), 1f));

        Button publish = actionButton("Publicar", true);
        publish.setOnClickListener(v -> runCommand("window.RotaAiAndroid.startPublish()"));
        bottomBar.addView(publish, new LinearLayout.LayoutParams(0, dp(52), 0.85f));

        root.addView(toolbar, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(56)));
        root.addView(progressBar, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(3)));
        root.addView(statusText, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        root.addView(webView, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f));
        root.addView(bottomBar, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(64)));
        setContentView(root);
    }

    private Button toolbarButton(String text) {
        Button button = new Button(this);
        button.setText(text);
        button.setTextSize(12);
        button.setAllCaps(false);
        button.setTextColor(Color.WHITE);
        button.setBackgroundColor(Color.TRANSPARENT);
        button.setPadding(dp(6), 0, dp(6), 0);
        button.setMinWidth(0);
        button.setMinimumWidth(0);
        button.setMinHeight(0);
        button.setMinimumHeight(0);
        return button;
    }

    private Button actionButton(String text, boolean primary) {
        Button button = new Button(this);
        button.setText(text);
        button.setTextSize(11);
        button.setAllCaps(false);
        button.setTextColor(primary ? Color.WHITE : Color.rgb(0, 90, 90));
        button.setBackgroundTintList(android.content.res.ColorStateList.valueOf(
                primary ? Color.rgb(0, 106, 106) : Color.rgb(230, 245, 244)));
        button.setPadding(dp(4), 0, dp(4), 0);
        button.setMinWidth(0);
        button.setMinimumWidth(0);
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
        settings.setTextZoom(100);
        settings.setMediaPlaybackRequiresUserGesture(true);
        settings.setUserAgentString(settings.getUserAgentString() + " RotaAiAvaliador/0.4.0");
        if (android.os.Build.VERSION.SDK_INT >= 26) settings.setSafeBrowsingEnabled(true);

        CookieManager cookieManager = CookieManager.getInstance();
        cookieManager.setAcceptCookie(true);
        cookieManager.setAcceptThirdPartyCookies(webView, true);

        webView.addJavascriptInterface(new AppBridge(), "RotaAiNative");
        WebView.setWebContentsDebuggingEnabled(false);
        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onProgressChanged(WebView view, int newProgress) {
                progressBar.setProgress(newProgress);
                progressBar.setVisibility(newProgress >= 100 ? View.GONE : View.VISIBLE);
            }
        });

        webView.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri uri = request.getUrl();
                if (isAllowedUri(uri)) return false;
                openExternally(uri);
                return true;
            }

            @Override
            public boolean shouldOverrideUrlLoading(WebView view, String url) {
                Uri uri = Uri.parse(url);
                if (isAllowedUri(uri)) return false;
                openExternally(uri);
                return true;
            }

            @Override
            public void onPageFinished(WebView view, String url) {
                super.onPageFinished(view, url);
                injectIfAllowed(url);
                handler.postDelayed(() -> injectIfAllowed(webView.getUrl()), 450);
                handler.postDelayed(() -> injectIfAllowed(webView.getUrl()), 1300);
            }

            @Override
            public void onSafeBrowsingHit(WebView view, WebResourceRequest request, int threatType,
                                          SafeBrowsingResponse callback) {
                callback.backToSafety(true);
                Toast.makeText(MainActivity.this,
                        "Navegação bloqueada pelo Safe Browsing.", Toast.LENGTH_LONG).show();
            }

            @Override
            public void onReceivedHttpError(WebView view, WebResourceRequest request,
                                            WebResourceResponse errorResponse) {
                if (request.isForMainFrame()) {
                    Toast.makeText(MainActivity.this,
                            "A página retornou erro " + errorResponse.getStatusCode() + ".",
                            Toast.LENGTH_SHORT).show();
                }
            }
        });
    }

    private void runCommand(String command) {
        injectIfAllowed(webView.getUrl());
        handler.postDelayed(() -> webView.evaluateJavascript(
                "(function(){try{if(!window.RotaAiAndroid)return 'missing';" + command
                        + ";return 'ok';}catch(e){return 'error:'+String(e&&e.message||e);}})()",
                result -> {
                    if (result == null) return;
                    if (result.contains("missing")) {
                        Toast.makeText(this, "A automação ainda está carregando. Tente novamente em um instante.", Toast.LENGTH_SHORT).show();
                        injectIfAllowed(webView.getUrl());
                    } else if (result.contains("error:")) {
                        Toast.makeText(this, "Falha ao iniciar a automação.", Toast.LENGTH_LONG).show();
                    }
                }), 220);
    }

    private void injectIfAllowed(String url) {
        if (url == null || !isAllowedUri(Uri.parse(url)) || injectionScript.isBlank()) return;
        webView.evaluateJavascript(injectionScript, value -> { });
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
        try {
            startActivity(new Intent(Intent.ACTION_VIEW, uri));
        } catch (Exception ignored) {
            Toast.makeText(this, "Não foi possível abrir este link.", Toast.LENGTH_SHORT).show();
        }
    }

    private String loadAsset(String name) {
        try (InputStream input = getAssets().open(name);
             ByteArrayOutputStream output = new ByteArrayOutputStream()) {
            byte[] buffer = new byte[8192];
            int read;
            while ((read = input.read(buffer)) >= 0) output.write(buffer, 0, read);
            String raw = output.toString(java.nio.charset.StandardCharsets.UTF_8).trim();
            if (raw.startsWith("H4sI")) {
                byte[] compressed = Base64.decode(raw, Base64.DEFAULT);
                try (GZIPInputStream gzip = new GZIPInputStream(new ByteArrayInputStream(compressed));
                     ByteArrayOutputStream decoded = new ByteArrayOutputStream()) {
                    while ((read = gzip.read(buffer)) >= 0) decoded.write(buffer, 0, read);
                    return decoded.toString(java.nio.charset.StandardCharsets.UTF_8);
                }
            }
            return raw;
        } catch (IOException | IllegalArgumentException error) {
            return "console.error('RotaAi: falha ao carregar " + name.replace("'", "") + "');";
        }
    }

    private void showFirstUseNotice() {
        new AlertDialog.Builder(this)
                .setTitle("Fluxo rápido")
                .setMessage("1. Faça login.\n2. Toque em Revisar pendentes.\n3. Confira o texto e use Aprovar/próxima.\n4. No final, toque em Publicar.\n\nO aplicativo não publica nada antes da sua aprovação.")
                .setPositiveButton("Entendi", null)
                .show();
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }

    public final class AppBridge {
        @JavascriptInterface
        public void status(String message) {
            runOnUiThread(() -> statusText.setText(message == null || message.isBlank()
                    ? "RotaAi pronto." : message));
        }
    }

    @Override
    protected void onResume() {
        super.onResume();
        handler.postDelayed(() -> injectIfAllowed(webView == null ? null : webView.getUrl()), 350);
    }

    @Override
    protected void onSaveInstanceState(Bundle outState) {
        Bundle state = new Bundle();
        webView.saveState(state);
        outState.putBundle(STATE_KEY, state);
        super.onSaveInstanceState(outState);
    }

    @Override
    public void onBackPressed() {
        if (webView.canGoBack()) webView.goBack();
        else super.onBackPressed();
    }

    @Override
    protected void onDestroy() {
        handler.removeCallbacksAndMessages(null);
        if (webView != null) {
            webView.stopLoading();
            webView.loadUrl("about:blank");
            webView.clearHistory();
            webView.removeAllViews();
            webView.destroy();
        }
        super.onDestroy();
    }
}