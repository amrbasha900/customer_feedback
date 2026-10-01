/**
 * Customer Follow-Up Enforcement
 *
 * ROOT CAUSE FIX:
 *   setup_cf_editor() was called inside setTimeout(80ms) which ran
 *   BEFORE frappe.ui.Dialog finished rendering the HTML field into the DOM.
 *   The element existed in the DOM but _cf_tokens was never set because
 *   setup never actually ran — the timer fired too early.
 *
 *   Fix: MutationObserver on d.$wrapper detects exactly when cf-editor-N
 *   appears in the DOM, then immediately calls setup. No more race condition.
 */

frappe.after_ajax(function () {
    if (!frappe.session || frappe.session.user === "Guest") return;
    check_and_block();
});

function check_and_block() {
    frappe.call({
        method: "customer_feedback.api.followup.has_pending_followups",
        callback: function (r) {
            if (!r.message || !r.message.pending) return;
            inject_block_styles();
            inject_block_overlay(r.message.customers);
        },
        error: function () { }
    });
}

// ─────────────────────────────────────────────────────────────────
// STYLES
// ─────────────────────────────────────────────────────────────────

function inject_block_styles() {
    if (document.getElementById("cf-block-styles")) return;
    let style = document.createElement("style");
    style.id = "cf-block-styles";
    style.textContent = `
        #cf-block-overlay {
            position: fixed; top:0; left:0;
            width:100vw; height:100vh;
            background: rgba(15,23,42,0.93);
            z-index: 99999;
            display: flex; align-items: center; justify-content: center;
            backdrop-filter: blur(5px);
            pointer-events: all;
        }
        #cf-block-inner {
            background: #fff; border-radius: 14px;
            padding: 36px 40px; max-width: 520px; width: 92%;
            text-align: center;
            box-shadow: 0 30px 70px rgba(0,0,0,0.45);
        }
        #cf-block-icon  { font-size: 44px; margin-bottom: 10px; }
        #cf-block-title { font-size: 21px; font-weight: 700; color: #1e293b; margin: 0 0 10px; }
        #cf-block-msg   { font-size: 14px; color: #475569; line-height: 1.6; margin-bottom: 20px; }
        #cf-customer-list {
            text-align: left; margin-bottom: 22px;
            max-height: 220px; overflow-y: auto;
            border: 1px solid #e2e8f0; border-radius: 8px;
            padding: 4px 0;
        }
        .cf-customer-row {
            display: flex; align-items: center; gap: 10px;
            padding: 9px 14px; cursor: pointer;
            border-bottom: 1px solid #f1f5f9;
            transition: background 0.15s; user-select: none;
        }
        .cf-customer-row:last-child { border-bottom: none; }
        .cf-customer-row:hover { background: #f8fafc; }
        .cf-customer-row.cf-done { opacity: 0.4; pointer-events: none; }
        .cf-customer-row input[type=checkbox] {
            width: 16px; height: 16px; accent-color: #2563eb;
            cursor: pointer; flex-shrink: 0;
        }
        .cf-customer-info { flex: 1; min-width: 0; }
        .cf-customer-info b     { font-size: 13px; color: #1e293b; display: block; }
        .cf-customer-info small { font-size: 11px; color: #94a3b8; }
        .cf-customer-badge {
            font-size: 10px; font-weight: 600; padding: 2px 8px;
            border-radius: 99px; background: #fef3c7; color: #92400e;
            white-space: nowrap; flex-shrink: 0;
        }
        .cf-customer-badge.overdue { background: #fee2e2; color: #991b1b; }
        #cf-start-btn {
            background: #2563eb; color: #fff; border: none;
            border-radius: 8px; padding: 11px 30px;
            font-size: 14px; font-weight: 600; cursor: pointer;
            transition: background 0.2s; width: 100%;
        }
        #cf-start-btn:hover    { background: #1d4ed8; }
        #cf-start-btn:disabled { background: #93c5fd; cursor: not-allowed; }
        .modal-backdrop { z-index: 100000 !important; }
        .modal.show     { z-index: 100001 !important; }
        body.cf-blocked > *:not(#cf-block-overlay) { pointer-events: none !important; }
        .cf-editor-wrap { position: relative; }
        .cf-editor {
            border: 1px solid #d1d5db; border-radius: 6px;
            min-height: 90px; padding: 8px 10px;
            font-size: 13px; line-height: 1.6; color: #111827;
            background: #fff; outline: none;
            word-break: break-word; white-space: pre-wrap;
        }
        .cf-editor:focus { border-color: #2563eb; box-shadow: 0 0 0 2px #dbeafe; }
        .cf-editor:empty::before {
            content: attr(data-placeholder); color: #9ca3af;
            pointer-events: none; position: absolute; top: 8px; left: 10px;
        }
        .cf-mention-chip {
            display: inline-block; color: #2563eb; font-weight: 600;
            background: #eff6ff; border-radius: 4px; padding: 0 3px;
            font-size: 13px; cursor: default; user-select: none;
        }
        .cf-mention-dropdown {
            position: absolute; background: #fff; border: 1px solid #e2e8f0;
            border-radius: 8px; box-shadow: 0 8px 24px rgba(0,0,0,0.14);
            z-index: 999999; min-width: 240px; max-height: 200px;
            overflow-y: auto; padding: 4px 0;
        }
        .cf-mention-item {
            display: flex; align-items: center; gap: 10px;
            padding: 8px 14px; cursor: pointer;
            font-size: 13px; color: #1e293b; transition: background 0.12s;
        }
        .cf-mention-item:hover, .cf-mention-item.cf-active { background: #eff6ff; }
        .cf-mention-avatar {
            width: 28px; height: 28px; border-radius: 50%;
            background: #2563eb; color: #fff;
            display: flex; align-items: center; justify-content: center;
            font-size: 11px; font-weight: 700; flex-shrink: 0;
        }
        .cf-mention-name  { font-weight: 600; line-height: 1.2; }
        .cf-mention-email { font-size: 11px; color: #94a3b8; }
        .cf-char-counter {
            display: block; margin-top: 5px;
            font-size: 12px; color: #94a3b8; transition: color 0.2s;
        }
    `;
    document.head.appendChild(style);
}

// ─────────────────────────────────────────────────────────────────
// QUILL HTML BUILDER
// ─────────────────────────────────────────────────────────────────

var CF_SITE = window.location.origin;

function tokens_to_quill_html(tokens) {
    let inner = tokens.map(function (t) {
        if (t.type === "text") {
            return t.value
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;");
        }
        if (t.type === "mention") {
            let profile_url = CF_SITE + "/app/user-profile/" + encodeURIComponent(t.email);
            let data_value = '<a href="' + profile_url + '" target="_blank">' + frappe.utils.escape_html(t.label);
            let attr_value = data_value
                .replace(/&/g, "&amp;").replace(/"/g, "&quot;")
                .replace(/</g, "&lt;").replace(/>/g, "&gt;");
            return (
                '<span class="mention" ' +
                'data-id="' + frappe.utils.escape_html(t.email) + '" ' +
                'data-value="' + attr_value + '" ' +
                'data-denotation-char="@" data-is-group="false" ' +
                'data-link="' + profile_url + '">' +
                '\uFEFF' +
                '<span contenteditable="false">' +
                '<span class="ql-mention-denotation-char">@</span>' +
                '<a href="' + profile_url + '" target="_blank">' + frappe.utils.escape_html(t.label) + '</a>' +
                '</span>\uFEFF</span>'
            );
        }
        return "";
    }).join("");
    return '<div class="ql-editor read-mode"><p>' + inner + '</p><p><br></p></div>';
}

// ─────────────────────────────────────────────────────────────────
// HELPERS
// ─────────────────────────────────────────────────────────────────

function editor_plain_length(editor) {
    return (editor.innerText || "")
        .replace(/\uFEFF/g, "")
        .replace(/\u00A0/g, " ")
        .trim()
        .length;
}

function cf_rebuild_tokens_from(editor) {
    var tokens = [];
    function walk(node) {
        if (node.nodeType === Node.TEXT_NODE) {
            var val = node.textContent.replace(/\uFEFF/g, "");
            if (val) tokens.push({ type: "text", value: val });
        } else if (node.nodeType === Node.ELEMENT_NODE) {
            if (node.classList.contains("cf-mention-chip")) {
                tokens.push({ type: "mention", email: node.dataset.email, label: node.dataset.label });
            } else {
                node.childNodes.forEach(walk);
            }
        }
    }
    editor.childNodes.forEach(walk);
    var merged = [];
    tokens.forEach(function (t) {
        if (t.type === "text" && merged.length && merged[merged.length - 1].type === "text") {
            merged[merged.length - 1].value += t.value;
        } else { merged.push(t); }
    });
    return merged;
}

// ─────────────────────────────────────────────────────────────────
// WAIT FOR EDITOR — MutationObserver, replaces setTimeout
// Fires the instant cf-editor-N appears inside the dialog wrapper.
// ─────────────────────────────────────────────────────────────────

function wait_for_editor(wrapper_el, editor_id, counter_id, callback) {
    // Already present?
    var el = document.getElementById(editor_id);
    if (el) { callback(el, document.getElementById(counter_id)); return; }

    var observer = new MutationObserver(function () {
        var el = document.getElementById(editor_id);
        if (!el) return;
        observer.disconnect();
        callback(el, document.getElementById(counter_id));
    });

    observer.observe(wrapper_el, { childList: true, subtree: true });

    // Safety: disconnect after 5s if something goes very wrong
    setTimeout(function () { observer.disconnect(); }, 5000);
}

// ─────────────────────────────────────────────────────────────────
// OVERLAY
// ─────────────────────────────────────────────────────────────────

function inject_block_overlay(customers) {
    remove_block_overlay();

    var list_html = customers.map(function (c, i) {
        var last = c.last_followup_date || "Never";
        var delay = c.followup_delay_days || 1;
        var badge = last === "Never"
            ? '<span class="cf-customer-badge overdue">Never</span>'
            : '<span class="cf-customer-badge">Every ' + delay + 'd</span>';
        return '<label class="cf-customer-row" data-idx="' + i + '">' +
            '<input type="checkbox" class="cf-cust-check" value="' + i + '" checked>' +
            '<div class="cf-customer-info">' +
            '<b>' + frappe.utils.escape_html(c.customer_name) + '</b>' +
            '<small>Last follow-up: ' + last + '</small>' +
            '</div>' + badge + '</label>';
    }).join("");

    var overlay = document.createElement("div");
    overlay.id = "cf-block-overlay";
    overlay.innerHTML =
        '<div id="cf-block-inner">' +
        '<div id="cf-block-icon">🔒</div>' +
        '<h2 id="cf-block-title">System Restricted</h2>' +
        '<p id="cf-block-msg">You have <strong id="cf-pending-count">' + customers.length + '</strong> ' +
        'pending follow-up(s). Select customers to follow up — <em>all must be completed to unlock the system.</em></p>' +
        '<div id="cf-customer-list">' + list_html + '</div>' +
        '<button id="cf-start-btn">Start Follow-Ups →</button>' +
        '</div>';

    document.body.appendChild(overlay);
    document.body.classList.add("cf-blocked");

    overlay.querySelectorAll(".cf-cust-check").forEach(function (cb) {
        cb.addEventListener("change", function () {
            var n = overlay.querySelectorAll(".cf-cust-check:checked").length;
            var el = document.getElementById("cf-pending-count");
            if (el) el.textContent = n;
        });
    });

    document.getElementById("cf-start-btn").addEventListener("click", function () {
        var checked = Array.from(document.querySelectorAll(".cf-cust-check:checked"))
            .map(function (cb) { return customers[parseInt(cb.value)]; });
        if (!checked.length) {
            frappe.msgprint({ title: "No Customers Selected", message: "Select at least one customer.", indicator: "orange" });
            return;
        }
        this.disabled = true;
        this.textContent = "Loading...";
        show_followup_dialog(checked, customers);
    });
}

function remove_block_overlay() {
    var el = document.getElementById("cf-block-overlay");
    if (el) el.remove();
    document.body.classList.remove("cf-blocked");
}

function update_overlay_count(n) {
    var el = document.getElementById("cf-pending-count");
    if (el) el.textContent = n;
}

function mark_overlay_done(customer_name) {
    document.querySelectorAll(".cf-customer-row").forEach(function (row) {
        var b = row.querySelector("b");
        if (b && b.textContent === customer_name) row.classList.add("cf-done");
    });
}

function unlock_system() {
    remove_block_overlay();
    frappe.call({ method: "customer_feedback.api.followup.clear_followup_cache" });
    frappe.show_alert({ message: "✅ All follow-ups completed! System unlocked.", indicator: "green" }, 6);
}

// ─────────────────────────────────────────────────────────────────
// DIALOG SEQUENCE
// ─────────────────────────────────────────────────────────────────

function show_followup_dialog(selected, all_customers) {
    var index = 0;
    var active_dialog = null;

    function destroy_active() {
        if (!active_dialog) return;
        try {
            active_dialog.hide();
            document.querySelectorAll(".modal-backdrop").forEach(function (el) { el.remove(); });
            if (active_dialog.$wrapper) active_dialog.$wrapper.remove();
        } catch (e) { }
        active_dialog = null;
        document.body.classList.remove("modal-open");
        document.body.style.paddingRight = "";
    }

    function show_next() {
        destroy_active();

        if (index >= selected.length) {
            var done_names = selected.map(function (c) { return c.name; });
            var still_pending = all_customers.filter(function (c) { return !done_names.includes(c.name); });
            if (!still_pending.length) {
                unlock_system();
            } else {
                var btn = document.getElementById("cf-start-btn");
                if (btn) { btn.disabled = false; btn.textContent = "Continue (" + still_pending.length + " remaining) →"; }
                update_overlay_count(still_pending.length);
            }
            return;
        }

        var c = selected[index];
        var total = selected.length;
        var remaining_after = total - index - 1;
        var editor_id = "cf-editor-" + index;
        var counter_id = "cf-counter-" + index;

        var info_html = remaining_after > 0
            ? '<div style="background:#fef2f2;border:1px solid #fecaca;border-radius:6px;padding:8px 13px;margin-bottom:11px;font-size:12px;color:#dc2626;font-weight:600">⚠️ ' + remaining_after + ' more follow-up(s) after this.</div>'
            : '<div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:6px;padding:8px 13px;margin-bottom:11px;font-size:12px;color:#16a34a;font-weight:600">🏁 Last follow-up — submit to unlock the system.</div>';

        var d = new frappe.ui.Dialog({
            title: "📋 Follow-Up " + (index + 1) + " of " + total,
            static: true,
            fields: [{
                fieldtype: "HTML",
                options:
                    '<div style="background:#eff6ff;border-left:4px solid #3b82f6;padding:11px 15px;border-radius:6px;margin-bottom:11px">' +
                    '<b style="font-size:14px;color:#1e40af">' + frappe.utils.escape_html(c.customer_name) + '</b><br>' +
                    '<small style="color:#64748b">Last: <b>' + (c.last_followup_date || "Never") + '</b> &nbsp;·&nbsp; Every <b>' + (c.followup_delay_days || 1) + '</b> day(s)</small>' +
                    '</div>' + info_html +
                    '<label style="font-size:12px;font-weight:600;color:#374151;display:block;margin-bottom:6px">' +
                    'Follow-Up Comment <span style="font-weight:400;color:#6b7280">— type @ to mention a user</span></label>' +
                    '<div class="cf-editor-wrap">' +
                    '<div id="' + editor_id + '" class="cf-editor" contenteditable="true" spellcheck="true" ' +
                    'data-placeholder="What was discussed? Type @ to mention someone..."></div>' +
                    '</div>' +
                    '<span class="cf-char-counter" id="' + counter_id + '">0 / 20 characters minimum</span>'
            }],
            primary_action_label: remaining_after > 0 ? "Submit & Next →" : "Submit & Unlock ✅",
            primary_action: function () {
                var editor = document.getElementById(editor_id);
                if (!editor) {
                    frappe.msgprint({ title: "Error", message: "Editor not found — please refresh.", indicator: "red" });
                    return;
                }

                // Always use innerText as source of truth for char count
                var char_count = editor_plain_length(editor);
                if (char_count < 20) {
                    frappe.msgprint({
                        title: __("Comment Too Short"),
                        message: __("Minimum <b>20 characters</b> required. You entered <b>" + char_count + "</b>."),
                        indicator: "red"
                    });
                    return;
                }

                // Fresh token rebuild right before sending
                var tokens = cf_rebuild_tokens_from(editor);
                var quill_html = tokens_to_quill_html(tokens);

                d.disable_primary_action();
                d.set_title("Saving...");

                frappe.call({
                    method: "customer_feedback.api.followup.submit_followup_comment",
                    args: { customer: c.name, comment: quill_html },
                    callback: function (r) {
                        if (r.message && r.message.success) {
                            mark_overlay_done(c.customer_name);
                            update_overlay_count(total - index - 1);
                            frappe.show_alert({ message: "✅ Saved for " + c.customer_name, indicator: "green" }, 3);
                            index++;
                            show_next();
                        } else {
                            d.enable_primary_action();
                            d.set_title("📋 Follow-Up " + (index + 1) + " of " + total);
                        }
                    },
                    error: function () {
                        d.enable_primary_action();
                        d.set_title("📋 Follow-Up " + (index + 1) + " of " + total);
                    }
                });
            }
        });

        active_dialog = d;
        d.$wrapper.find(".btn-modal-close").hide();
        d.$wrapper.on("keydown", function (e) {
            if (e.key === "Escape") { e.stopPropagation(); e.preventDefault(); return false; }
        });
        d.$wrapper.on("shown.bs.modal", function () {
            var ov = document.getElementById("cf-block-overlay");
            if (ov) document.body.appendChild(ov);
        });

        d.show();

        // ── KEY FIX: MutationObserver waits for the HTML field to render ──
        // d.$wrapper[0] is the native DOM element of the Bootstrap modal.
        // The observer fires the instant cf-editor-N appears anywhere
        // inside it — no setTimeout guessing required.
        wait_for_editor(d.$wrapper[0], editor_id, counter_id, function (editor, counter) {
            setup_cf_editor(editor, counter);
            editor.focus();
        });
    }

    show_next();
}

// ─────────────────────────────────────────────────────────────────
// EDITOR SETUP
// ─────────────────────────────────────────────────────────────────

function setup_cf_editor(editor, counter) {
    editor._cf_tokens = [];
    editor._cf_ready = true;   // sentinel so we can verify setup ran

    var dropdown = null;
    var active_idx = -1;
    var mention_range = null;
    var is_composing = false;

    function update_counter() {
        if (!counter) return;
        var n = editor_plain_length(editor);
        counter.textContent = n + " / 20 characters minimum";
        counter.style.color = n >= 20 ? "#16a34a" : "#dc2626";
    }

    function rebuild_tokens() {
        editor._cf_tokens = cf_rebuild_tokens_from(editor);
    }

    function check_for_mention() {
        var sel = window.getSelection();
        if (!sel || !sel.rangeCount) { close_dropdown(); return; }
        var range = sel.getRangeAt(0);
        var node = range.startContainer;
        var offset = range.startOffset;
        if (node.nodeType !== Node.TEXT_NODE) { close_dropdown(); return; }
        var text_before = node.textContent.slice(0, offset);
        var at_pos = text_before.lastIndexOf("@");
        if (at_pos === -1) { close_dropdown(); return; }
        var query = text_before.slice(at_pos + 1);
        if (query.includes(" ")) { close_dropdown(); return; }
        var r = range.cloneRange();
        r.setStart(node, at_pos);
        r.collapse(true);
        mention_range = r;
        open_dropdown(query);
    }

    function close_dropdown() {
        if (dropdown) { dropdown.remove(); dropdown = null; }
        active_idx = -1;
        mention_range = null;
    }

    function initials(name) {
        return (name || "?").split(" ").map(function (w) { return w[0] || ""; })
            .join("").toUpperCase().slice(0, 2);
    }

    function open_dropdown(query) {
        close_dropdown();
        get_mention_users(function (all_users) {
            var filtered = all_users.filter(function (u) {
                var q = query.toLowerCase();
                return u.full_name.toLowerCase().includes(q) || u.name.toLowerCase().includes(q);
            }).slice(0, 10);
            if (!filtered.length) return;

            dropdown = document.createElement("div");
            dropdown.className = "cf-mention-dropdown";

            filtered.forEach(function (u) {
                var item = document.createElement("div");
                item.className = "cf-mention-item";
                item.dataset.email = u.name;
                item.dataset.label = u.full_name;
                item.innerHTML =
                    '<div class="cf-mention-avatar">' + initials(u.full_name) + '</div>' +
                    '<div><div class="cf-mention-name">' + frappe.utils.escape_html(u.full_name) + '</div>' +
                    '<div class="cf-mention-email">' + frappe.utils.escape_html(u.name) + '</div></div>';
                item.addEventListener("mousedown", function (e) {
                    e.preventDefault();
                    insert_mention(u.name, u.full_name);
                });
                dropdown.appendChild(item);
            });

            var wrap = editor.parentElement;
            wrap.style.position = "relative";
            wrap.appendChild(dropdown);
            set_active(0);
        });
    }

    function set_active(i) {
        if (!dropdown) return;
        var items = dropdown.querySelectorAll(".cf-mention-item");
        items.forEach(function (el) { el.classList.remove("cf-active"); });
        active_idx = Math.max(0, Math.min(i, items.length - 1));
        if (items[active_idx]) {
            items[active_idx].classList.add("cf-active");
            items[active_idx].scrollIntoView({ block: "nearest" });
        }
    }

    function insert_mention(email, label) {
        var sel = window.getSelection();
        if (sel.rangeCount && mention_range) {
            var del_range = mention_range.cloneRange();
            del_range.setEnd(sel.anchorNode, sel.anchorOffset);
            del_range.deleteContents();
        }
        var chip = document.createElement("span");
        chip.className = "cf-mention-chip";
        chip.contentEditable = "false";
        chip.dataset.email = email;
        chip.dataset.label = label;
        chip.textContent = "@" + label;

        var space = document.createTextNode("\u00A0");
        var range = window.getSelection().getRangeAt(0);
        range.insertNode(space);
        range.insertNode(chip);
        range.setStartAfter(space);
        range.collapse(true);
        sel.removeAllRanges();
        sel.addRange(range);

        close_dropdown();
        rebuild_tokens();
        update_counter();
        editor.focus();
    }

    // IME
    editor.addEventListener("compositionstart", function () { is_composing = true; });
    editor.addEventListener("compositionend", function () {
        is_composing = false;
        rebuild_tokens();
        update_counter();
        check_for_mention();
    });

    // input
    editor.addEventListener("input", function () {
        update_counter();
        if (is_composing) return;
        rebuild_tokens();
        check_for_mention();
    });

    // keydown
    editor.addEventListener("keydown", function (e) {
        if (dropdown) {
            var items = dropdown.querySelectorAll(".cf-mention-item");
            if (e.key === "ArrowDown") { e.preventDefault(); set_active(active_idx + 1); return; }
            if (e.key === "ArrowUp") { e.preventDefault(); set_active(active_idx - 1); return; }
            if ((e.key === "Enter" || e.key === "Tab") && items[active_idx]) {
                e.preventDefault();
                insert_mention(items[active_idx].dataset.email, items[active_idx].dataset.label);
                return;
            }
            if (e.key === "Escape") { close_dropdown(); return; }
        }
        if (e.key === "Enter") { e.preventDefault(); }
    });

    editor.addEventListener("blur", function () { setTimeout(close_dropdown, 200); });
    editor.addEventListener("paste", function (e) {
        e.preventDefault();
        var text = (e.clipboardData || window.clipboardData).getData("text/plain");
        document.execCommand("insertText", false, text);
    });
}

// ─────────────────────────────────────────────────────────────────
// USER CACHE
// ─────────────────────────────────────────────────────────────────

var _mention_users_cache = null;

function get_mention_users(callback) {
    if (_mention_users_cache) { callback(_mention_users_cache); return; }
    frappe.call({
        method: "frappe.client.get_list",
        args: {
            doctype: "User",
            filters: [["enabled", "=", 1], ["user_type", "=", "System User"]],
            fields: ["name", "full_name"],
            limit_page_length: 200
        },
        callback: function (r) {
            _mention_users_cache = r.message || [];
            callback(_mention_users_cache);
        }
    });
}