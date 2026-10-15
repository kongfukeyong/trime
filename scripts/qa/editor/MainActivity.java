package local.trime.qa.editor;

import android.app.Activity;
import android.content.Intent;
import android.os.Bundle;
import android.text.Editable;
import android.text.TextWatcher;
import android.text.InputType;
import android.view.Gravity;
import android.view.inputmethod.InputMethodManager;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.TextView;

/** Test-only editor. No network, product code or IME simulation. */
public class MainActivity extends Activity {
    private EditText editor;
    private TextView observed;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        int pad = (int) (16 * getResources().getDisplayMetrics().density);
        root.setPadding(pad, pad, pad, pad);
        TextView title = new TextView(this);
        title.setText("Trime QA: ordinary text editor");
        title.setTextSize(20);
        root.addView(title);
        LinearLayout row = new LinearLayout(this);
        root.addView(row);
        addSeed(row, "Clear", "");
        addSeed(row, "hello", "hello");
        addSeed(row, "你好", "你好");
        editor = new EditText(this);
        editor.setId(0x1001);
        editor.setContentDescription("QA ordinary text field");
        editor.setHint("Tap AUTO in the IME, then type nihao");
        editor.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_FLAG_MULTI_LINE);
        editor.setGravity(Gravity.TOP | Gravity.START);
        editor.setMinLines(3);
        root.addView(editor, new LinearLayout.LayoutParams(-1, 0, 1));
        observed = new TextView(this);
        observed.setContentDescription("Editor contents and composing range");
        root.addView(observed);
        editor.addTextChangedListener(new TextWatcher() {
            public void beforeTextChanged(CharSequence s, int start, int count, int after) {}
            public void onTextChanged(CharSequence s, int start, int before, int count) {}
            public void afterTextChanged(Editable text) {
                int start = android.view.inputmethod.BaseInputConnection.getComposingSpanStart(text);
                int end = android.view.inputmethod.BaseInputConnection.getComposingSpanEnd(text);
                observed.setText("Text: [" + text + "]\nComposing: " + start + ".." + end);
            }
        });
        setContentView(root);
        seed(getIntent().getStringExtra("text") == null ? "" : getIntent().getStringExtra("text"));
    }

    private void addSeed(LinearLayout row, String label, final String text) {
        Button button = new Button(this);
        button.setAllCaps(false);
        button.setText(label);
        button.setOnClickListener(v -> seed(text));
        row.addView(button, new LinearLayout.LayoutParams(0, -2, 1));
    }

    private void seed(String text) {
        editor.setText(text);
        editor.setSelection(editor.length());
        editor.requestFocus();
        editor.postDelayed(() -> {
            InputMethodManager manager = (InputMethodManager) getSystemService(INPUT_METHOD_SERVICE);
            manager.restartInput(editor);
            manager.showSoftInput(editor, InputMethodManager.SHOW_IMPLICIT);
        }, 150);
    }

    @Override protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        if (intent.hasExtra("text")) seed(intent.getStringExtra("text"));
    }
}
