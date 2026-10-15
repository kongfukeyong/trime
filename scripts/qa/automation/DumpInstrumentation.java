package local.trime.qa.automation;

import android.accessibilityservice.AccessibilityServiceInfo;
import android.app.Activity;
import android.app.Instrumentation;
import android.app.UiAutomation;
import android.graphics.Rect;
import android.os.Bundle;
import android.os.SystemClock;
import android.util.Xml;
import android.view.accessibility.AccessibilityNodeInfo;
import android.view.accessibility.AccessibilityWindowInfo;
import java.io.StringWriter;
import java.nio.charset.StandardCharsets;
import java.util.List;
import org.xmlpull.v1.XmlSerializer;

/** Targets only this helper package: never starts or instruments the editor/IME. */
public final class DumpInstrumentation extends Instrumentation {
    private int nodeCount;

    @Override public void onCreate(Bundle arguments) {
        super.onCreate(arguments);
        start();
    }

    @Override public void onStart() {
        Bundle result = new Bundle();
        try {
            UiAutomation automation = getUiAutomation(UiAutomation.FLAG_DONT_SUPPRESS_ACCESSIBILITY_SERVICES);
            AccessibilityServiceInfo info = automation.getServiceInfo();
            info.flags |= AccessibilityServiceInfo.FLAG_RETRIEVE_INTERACTIVE_WINDOWS
                    | AccessibilityServiceInfo.FLAG_REPORT_VIEW_IDS
                    | AccessibilityServiceInfo.FLAG_INCLUDE_NOT_IMPORTANT_VIEWS;
            automation.setServiceInfo(info);
            long deadline = SystemClock.uptimeMillis() + 5000;
            String document = null;
            int windowCount = 0;
            do {
                SystemClock.sleep(150);
                nodeCount = 0;
                StringWriter writer = new StringWriter();
                XmlSerializer xml = Xml.newSerializer();
                xml.setOutput(writer);
                xml.startTag(null, "hierarchy");
                xml.attribute(null, "source", "all-windows");
                List<AccessibilityWindowInfo> windows = automation.getWindows();
                windowCount = windows.size();
                for (AccessibilityWindowInfo window : windows) {
                    try {
                        AccessibilityNodeInfo root = window.getRoot();
                        if (root == null) continue;
                        xml.startTag(null, "window");
                        xml.attribute(null, "id", Integer.toString(window.getId()));
                        xml.attribute(null, "type", Integer.toString(window.getType()));
                        xml.attribute(null, "layer", Integer.toString(window.getLayer()));
                        try { writeNode(xml, root, 0, 0); }
                        finally { root.recycle(); }
                        xml.endTag(null, "window");
                    } finally { window.recycle(); }
                }
                xml.endTag(null, "hierarchy");
                xml.flush();
                if (nodeCount > 0) document = writer.toString();
            } while (document == null && SystemClock.uptimeMillis() < deadline);
            if (document == null) throw new IllegalStateException("No visible nodes in interactive windows");
            // No declaration/formatting/text nodes: literal newlines can only occur
            // inside attribute values. Keep `am instrument` output on one line.
            document = document.replace("\r", "&#13;").replace("\n", "&#10;");
            if (document.getBytes(StandardCharsets.UTF_8).length > 512 * 1024) {
                throw new IllegalStateException("XML exceeds safe instrumentation result size");
            }
            result.putString("xml", document);
            result.putString("qa_dump_status", "ok");
            result.putInt("windows", windowCount);
            result.putInt("nodes", nodeCount);
            finish(Activity.RESULT_OK, result);
        } catch (Exception error) {
            result.putString("qa_dump_status", "error");
            result.putString("qa_dump_error", error.toString());
            finish(Activity.RESULT_CANCELED, result);
        }
    }

    private void writeNode(XmlSerializer xml, AccessibilityNodeInfo node, int index, int depth) throws Exception {
        if (depth > 128) throw new IllegalStateException("Accessibility hierarchy depth limit");
        Rect bounds = new Rect();
        node.getBoundsInScreen(bounds);
        boolean include = node.isVisibleToUser() && !bounds.isEmpty();
        if (include) {
            if (++nodeCount > 10000) throw new IllegalStateException("Accessibility node limit");
            xml.startTag(null, "node");
            attr(xml, "index", Integer.toString(index));
            attr(xml, "text", node.getText());
            attr(xml, "resource-id", node.getViewIdResourceName());
            attr(xml, "class", node.getClassName());
            attr(xml, "package", node.getPackageName());
            attr(xml, "content-desc", node.getContentDescription());
            attr(xml, "bounds", "["+bounds.left+","+bounds.top+"]["+bounds.right+","+bounds.bottom+"]");
            attr(xml, "enabled", Boolean.toString(node.isEnabled()));
            attr(xml, "checkable", Boolean.toString(node.isCheckable()));
            attr(xml, "checked", Boolean.toString(node.isChecked()));
            attr(xml, "clickable", Boolean.toString(node.isClickable()));
            attr(xml, "focusable", Boolean.toString(node.isFocusable()));
            attr(xml, "focused", Boolean.toString(node.isFocused()));
            attr(xml, "selected", Boolean.toString(node.isSelected()));
            attr(xml, "scrollable", Boolean.toString(node.isScrollable()));
            attr(xml, "long-clickable", Boolean.toString(node.isLongClickable()));
            attr(xml, "password", Boolean.toString(node.isPassword()));
        }
        // Traverse children even if a container itself is invisible/empty.
        for (int i = 0; i < node.getChildCount(); i++) {
            AccessibilityNodeInfo child = node.getChild(i);
            if (child == null) continue;
            try { writeNode(xml, child, i, depth+1); }
            finally { child.recycle(); }
        }
        if (include) xml.endTag(null, "node");
    }

    private static void attr(XmlSerializer xml, String name, CharSequence value) throws Exception {
        StringBuilder clean = new StringBuilder();
        if (value != null) {
            String text = value.toString();
            for (int offset = 0; offset < text.length();) {
                int cp = text.codePointAt(offset);
                if (cp == 9 || cp == 10 || cp == 13 || (cp >= 32 && cp <= 0xD7FF)
                        || (cp >= 0xE000 && cp <= 0xFFFD) || (cp >= 0x10000 && cp <= 0x10FFFF)) {
                    clean.appendCodePoint(cp);
                } else { clean.append('\uFFFD'); }
                offset += Character.charCount(cp);
            }
        }
        xml.attribute(null, name, clean.toString());
    }
}
