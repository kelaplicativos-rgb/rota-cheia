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

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.util.Locale;
import java.io.ByteArrayInputStream;
import java.util.zip.GZIPInputStream;

public final class MainActivity extends Activity {
    private static final String HOME_URL = "https://www.blablacar.com.br/rides";
    private static final String STATE_KEY = "webview_state";

    private WebView webView;
    private ProgressBar progressBar;
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
        toolbar.setPadding(dp(8), dp(6), dp(8), dp(6));
        toolbar.setBackgroundColor(Color.rgb(0, 106, 106));

        TextView title = new TextView(this);
        title.setText("RotaAi Avaliações");
        title.setTextColor(Color.WHITE);
        title.setTextSize(18);
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

        Button panel = toolbarButton("Painel");
        panel.setOnClickListener(v -> webView.evaluateJavascript(
                "window.RotaAiAndroid && window.RotaAiAndroid.openPanel && window.RotaAiAndroid.openPanel();",
                null));
        toolbar.addView(panel);

        progressBar = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
        progressBar.setMax(100);
        progressBar.setProgress(0);
        progressBar.setVisibility(View.GONE);

        webView = new WebView(this);
        root.addView(toolbar, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(58)));
        root.addView(progressBar, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(3)));
        root.addView(webView, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f));
        setContentView(root);
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

    @SuppressLint("SetJavaScriptEnabled")
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
        settings.setUserAgentString(settings.getUserAgentString() + " RotaAiAvaliador/0.3.0");
        if (android.os.Build.VERSION.SDK_INT >= 26) {
            settings.setSafeBrowsingEnabled(true);
        }

        CookieManager cookieManager = CookieManager.getInstance();
        cookieManager.setAcceptCookie(true);
        cookieManager.setAcceptThirdPartyCookies(webView, true);

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
                handler.postDelayed(() -> injectIfAllowed(webView.getUrl()), 900);
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

    private void injectIfAllowed(String url) {
        if (url == null || !isAllowedUri(Uri.parse(url)) || injectionScript.isBlank()) return;
        webView.evaluateJavascript(injectionScript, value -> {
            // O painel cuida da própria interface. Nenhum dado de login é lido pelo código nativo.
        });
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
                .setTitle("Como funciona")
                .setMessage("Faça login somente nas páginas oficiais da BlaBlaCar. "
                        + "O RotaAi localiza apenas quem ainda precisa ser avaliado, entra no perfil, "
                        + "usa avaliações existentes como base e preenche o texto para sua conferência. "
                        + "Nada é publicado até você aprovar cada pessoa e tocar em “Publicar aprovadas”.")
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
