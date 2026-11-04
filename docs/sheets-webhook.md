# Sync Kapaat to Google Sheets

Kapaat can send every change (item added, moved, checked out, retired, bin created…) to a webhook URL. This guide sets up a free Google Apps Script that receives those changes and keeps a spreadsheet up to date. Nothing else is required: no n8n, no Zapier, no Google Cloud project.

The sheet is a **read-only mirror**. Edits made in the sheet are not sent back to Kapaat.

## 1. Create the spreadsheet and script

1. Create a new Google Sheet (any name).
2. Open **Extensions → Apps Script**.
3. Replace the contents of `Code.gs` with the script below.
4. Change `KEY` to a long random string (for example the output of `openssl rand -hex 24`). Anyone who knows the full URL including this key can write to your sheet, so treat it like a password.
5. Click **Save**.

```javascript
// Kapaat → Google Sheets mirror. Paste into Extensions → Apps Script.
const KEY = "change-me-to-a-long-random-string";

const ITEM_COLS = ["id", "name", "qty", "category", "bin", "room", "zone", "tags", "checked_out", "status", "notes"];
const BIN_COLS = ["id", "code", "name", "room", "zone", "status", "color"];
const LOG_COLS = ["at", "event", "user", "what"];

function doPost(e) {
  if (!e || !e.parameter || e.parameter.key !== KEY) {
    return ContentService.createTextOutput("forbidden");
  }
  const ev = JSON.parse(e.postData.contents);
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const lock = LockService.getScriptLock();
  lock.waitLock(20000);
  try {
    if (ev.event === "inventory.snapshot") {
      replaceAll(sheet(ss, "Items", ITEM_COLS), ITEM_COLS, ev.data.items);
      replaceAll(sheet(ss, "Bins", BIN_COLS), BIN_COLS, ev.data.bins);
    } else if (ev.entity === "item" && ev.data && ev.data.id) {
      upsert(sheet(ss, "Items", ITEM_COLS), ITEM_COLS, ev.data);
    } else if (ev.entity === "bin" && ev.data && ev.data.id) {
      upsert(sheet(ss, "Bins", BIN_COLS), BIN_COLS, ev.data);
    }
    const what = ev.data ? ev.data.name || ev.data.code || "" : "";
    sheet(ss, "Log", LOG_COLS).appendRow([ev.at, ev.event, ev.user || "", what]);
  } finally {
    lock.releaseLock();
  }
  return ContentService.createTextOutput("ok");
}

function sheet(ss, name, cols) {
  let sh = ss.getSheetByName(name);
  if (!sh) {
    sh = ss.insertSheet(name);
    sh.appendRow(cols);
    sh.setFrozenRows(1);
    sh.getRange(1, 1, 1, cols.length).setFontWeight("bold");
  }
  return sh;
}

function toRow(cols, data) {
  return cols.map((c) => {
    const v = data[c];
    if (Array.isArray(v)) return v.join(", ");
    if (v === null || v === undefined) return "";
    if (typeof v === "string" && /^[=+\-@]/.test(v)) return "'" + v; // never let data become a formula
    return v;
  });
}

function upsert(sh, cols, data) {
  const ids = sh.getRange(2, 1, Math.max(sh.getLastRow() - 1, 1), 1).getValues().map((r) => String(r[0]));
  const idx = ids.indexOf(String(data.id));
  const row = toRow(cols, data);
  if (idx >= 0) sh.getRange(idx + 2, 1, 1, cols.length).setValues([row]);
  else sh.appendRow(row);
}

function replaceAll(sh, cols, rows) {
  if (sh.getLastRow() > 1) sh.getRange(2, 1, sh.getLastRow() - 1, cols.length).clearContent();
  if (rows.length) sh.getRange(2, 1, rows.length, cols.length).setValues(rows.map((r) => toRow(cols, r)));
}
```

## 2. Deploy it as a web app

1. Click **Deploy → New deployment**, choose type **Web app**.
2. *Execute as*: **Me**. *Who has access*: **Anyone**. (Kapaat's server is not signed in to Google; the `KEY` check in the script is what keeps strangers out.)
3. Click **Deploy**, authorise the script, and copy the **Web app URL**. It ends in `/exec`.

## 3. Connect Kapaat

1. In Kapaat, open **More → Google Sheets / webhook** (admins only).
2. Paste the web app URL and add your key: `https://script.google.com/macros/s/…/exec?key=YOUR_KEY`
3. Click **Save URL**, then **Send test**. You should see "Test delivered" and a row in the sheet's **Log** tab.
4. Click **Turn on**, then **Send full snapshot** to fill the **Items** and **Bins** tabs with everything you already have.

From then on every change appears in the sheet within a few seconds. Room and zone renames don't rewrite existing rows; press **Send full snapshot** again whenever you want a clean copy.

## How delivery works

- Changes are queued in Kapaat's database and sent in order, oldest first.
- If the webhook is down, Kapaat retries with backoff (30 s, 1 min, 2 min … up to 6 h) and holds later changes so the sheet never sees them out of order. After 8 failed attempts an event is parked; **Retry them** in settings re-queues parked events.
- Only changes made after you turn the webhook on are sent. Use **Send full snapshot** for the rest.

## Using another receiver (n8n, Home Assistant, your own code)

Each delivery is an HTTP `POST` with a JSON body:

```json
{
  "id": 42,
  "event": "item.moved",
  "entity": "item",
  "entity_id": 7,
  "action": "moved",
  "at": "2026-11-04T12:00:00+00:00",
  "user": "Priya",
  "data": { "id": 7, "name": "Tent", "qty": 2, "bin": "B-0003", "room": "Garage", "zone": "North wall",
            "tags": ["camping"], "checked_out": false, "status": "active", "from": "B-0001", "to": "B-0003" }
}
```

Events: `item.created`, `item.updated`, `item.moved`, `item.checked_out`, `item.checked_in`, `item.retired`, `item.restored`, `item.photo_updated`, `bin.created`, `bin.updated`, `bin.retired`, `bin.restored`, `room.*`, `zone.*`, `user.*`, `inventory.snapshot`, and `kapaat.ping` for tests.

Headers:

| Header | Value |
|---|---|
| `X-Kapaat-Event` | the event name |
| `X-Kapaat-Signature` | `sha256=` + hex HMAC-SHA256 of the raw body, keyed with the signing secret shown in settings |

Verify the signature when your receiver can read headers (Apps Script can't, which is why the guide above uses a URL key). Python example:

```python
import hashlib, hmac

def valid(secret: str, body: bytes, header: str) -> bool:
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header)
```

Any 2xx response counts as delivered. Redirects are followed.
