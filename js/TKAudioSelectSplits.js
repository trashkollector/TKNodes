import { app } from "../../scripts/app.js";

console.log("[TKAudioSelectSplits] JS LOADED");

const SLIDER_HEIGHT = 28;
const THUMB_RADIUS = 5;
const TRACK_PADDING = 16;
const ACTIVE_COLOR = "#4a9eff";
const INACTIVE_COLOR = "#555";
const THUMB_ACTIVE_COLOR = "#ffffff";
const THUMB_INACTIVE_COLOR = "#888";
const TRACK_BG = "#222";
const LABEL_COLOR = "#ccc";
const FONT_SIZE = 10;
const BTN_SIZE = 18;
const BTN_MARGIN = 6;

app.registerExtension({
    name: "extTKAudioSelectSplits",

    async beforeRegisterNodeDef(nodeType, nodeData, _app) {
        if (nodeData.name !== "TKAudioSelectSplits") return;

        const orig = nodeType.prototype.onNodeCreated;

        nodeType.prototype.onNodeCreated = function () {
            if (orig) orig.apply(this, arguments);

            setTimeout(() => {
                const MAX_SPLITS = 10;
                const node = this;

                // ── State ────────────────────────────────────────────────
                let duration = 0;        // 0 = not yet known; read from connected node
                let numActive = 1;       // how many thumbs are active
                let thumbs = [];         // array of { time, active }
                let dragIndex = -1;
                let dragOffsetX = 0;

                // ── Find or create the hidden value widget ───────────────
                let valueWidget = node.widgets?.find(w => w.name === "split_times");
                if (!valueWidget) {
                    valueWidget = node.addWidget("text", "split_times", "[]", () => { }, {
                        serialize: true,
                    });
                }
                // Show as read-only — user can see values but not edit directly
                valueWidget.disabled = true;

                // num_splits is pure JS state — no widget needed.
                // numActive is saved/restored via the split_times array length.

                // ── Initialize thumbs evenly spaced ──────────────────────
                function initThumbs() {
                    if (duration <= 0) return;
                    thumbs = [];
                    for (let i = 0; i < MAX_SPLITS; i++) {
                        const time = duration * (i + 1) / (MAX_SPLITS + 1);
                        thumbs.push({ time });
                    }
                    updateActive();
                }

                function updateActive() {
                    // Enforce sorted order after any change
                    thumbs.sort((a, b) => a.time - b.time);
                    serializeValue();
                }

                function serializeValue() {
                    const activeTimes = thumbs
                        .slice(0, numActive)
                        .map(t => parseFloat(t.time.toFixed(3)));
                    valueWidget.value = JSON.stringify(activeTimes);
                }

                // ── Geometry helpers ─────────────────────────────────────
                // Button row sits above the track row
                const BTN_ROW_H = 26;

                function getButtonBounds(node) {
                    const rowY = node.size[1] - SLIDER_HEIGHT - BTN_ROW_H - 18;
                    const cy = rowY + BTN_ROW_H / 2;
                    const totalW = BTN_SIZE * 2 + BTN_MARGIN * 2 + 28; // −  count  +
                    const startX = (node.size[0] - totalW) / 2;
                    const minusX = startX;
                    const labelX = minusX + BTN_SIZE + BTN_MARGIN;
                    const plusX = labelX + 28 + BTN_MARGIN;
                    return { minusX, labelX, plusX, cy, btnY: cy - BTN_SIZE / 2 };
                }

                function getTrackBounds(node) {
                    const x = TRACK_PADDING;
                    const w = node.size[0] - TRACK_PADDING * 2;
                    const y = node.size[1] - SLIDER_HEIGHT - 12;
                    return { x, y, w };
                }

                function timeToX(time, trackX, trackW) {
                    return trackX + (time / duration) * trackW;
                }

                function xToTime(px, trackX, trackW) {
                    return Math.max(0, Math.min(duration, ((px - trackX) / trackW) * duration));
                }

                // ── Draw ─────────────────────────────────────────────────
                const origDraw = nodeType.prototype.onDrawForeground;
                node.onDrawForeground = function (ctx) {
                    if (origDraw) origDraw.call(this, ctx);
                    if (this.flags?.collapsed) return;

                    const { x: tx, y: ty, w: tw } = getTrackBounds(this);
                    const cy = ty + SLIDER_HEIGHT / 2;

                    ctx.save();

                    // ── +/- buttons (always visible) ─────────────────────
                    const { minusX, labelX, plusX, cy: bcy, btnY } = getButtonBounds(this);
                    const drawBtn = (bx, label, enabled) => {
                        ctx.beginPath();
                        ctx.roundRect(bx, btnY, BTN_SIZE, BTN_SIZE, 4);
                        ctx.fillStyle = enabled ? "#000000" : "#2a2a2a";
                        ctx.fill();
                        ctx.strokeStyle = enabled ? "#fff" : "#333";
                        ctx.lineWidth = 1;
                        ctx.stroke();
                        ctx.fillStyle = enabled ? "#fff" : "#444";
                        ctx.font = `bold 13px sans-serif`;
                        ctx.textAlign = "center";
                        ctx.textBaseline = "middle";
                        ctx.fillText(label, bx + BTN_SIZE / 2, bcy);
                    };
                    drawBtn(minusX-10, "−", numActive > 1);
                    drawBtn(plusX+10, "+", numActive < MAX_SPLITS);
                    // Active count label between buttons
                    ctx.fillStyle = "#aaa";
                    ctx.font = `bold 11px monospace`;
                    ctx.textAlign = "center";
                    ctx.textBaseline = "middle";
                    ctx.fillText("SPLITS", labelX + BTN_SIZE / 2, bcy);

                    // ── No duration yet ──────────────────────────────────
                    if (duration <= 0) {
                        ctx.fillStyle = "#000";
                        ctx.font = `11px sans-serif`;
                        ctx.textAlign = "center";
                        ctx.textBaseline = "middle";
                        ctx.fillText("Connect audio and Run to load duration", tx + tw / 2, cy);
                        ctx.restore();
                        return;
                    }

                    // ── Track background ─────────────────────────────────
                    ctx.beginPath();
                    ctx.roundRect(tx, cy - 3, tw, 6, 3);
                    ctx.fillStyle = TRACK_BG;
                    ctx.fill();

                    // ── Tick marks (every second) ────────────────────────
                    const pxPerSec = tw / duration;
                    const totalSecs = Math.floor(duration);
                    for (let i = 0; i <= totalSecs; i++) {
                        const px = timeToX(i, tx, tw);
                        const isFive = (i % 5 === 0);
                        const tickH = isFive ? 7 : 4;
                        ctx.beginPath();
                        ctx.moveTo(px, cy + 4);
                        ctx.lineTo(px, cy + 4 + tickH);
                        ctx.strokeStyle = isFive ? "#000    " : "#000000";
                        ctx.lineWidth = isFive ? 1 : 0.5;
                        ctx.stroke();

                        // Label every 5s, skip 0, skip if too crowded
                        if (isFive && i > 0 && i < duration && pxPerSec * 5 > 24) {
                            ctx.fillStyle = "#000";
                            ctx.font = `8px monospace`;
                            ctx.textAlign = "center";
                            ctx.textBaseline = "top";
                            ctx.fillText(i + "s", px, cy + 13);
                        }
                    }

                    // ── Active segment highlight ──────────────────────────
                    if (numActive > 0 && thumbs.length >= numActive) {
                        const x0 = timeToX(thumbs[0].time, tx, tw);
                        const x1 = timeToX(thumbs[numActive - 1].time, tx, tw);
                        //ctx.beginPath();
                        //ctx.roundRect(x0, cy - 3, Math.max(0, x1 - x0), 6, 3);
                        //ctx.fillStyle = ACTIVE_COLOR;
                        //ctx.fill();
                    }

                    // ── Thumbs (active only) ─────────────────────────────
                    for (let i = 0; i < numActive; i++) {
                        const t = thumbs[i];
                        const px = timeToX(t.time, tx, tw);

                        ctx.beginPath();
                        ctx.arc(px, cy, THUMB_RADIUS, 0, Math.PI * 2);
                        ctx.fillStyle = ACTIVE_COLOR;
                        ctx.fill();
                        ctx.strokeStyle = THUMB_ACTIVE_COLOR;
                        ctx.lineWidth = 1.5;
                        ctx.stroke();

                        // Index label inside thumb
                        ctx.fillStyle = "#000";
                        ctx.font = `bold ${FONT_SIZE - 1}px monospace`;
                        ctx.textAlign = "center";
                        ctx.textBaseline = "middle";
                        ctx.fillText(i + 1, px, cy);

                        // Time label above thumb
                        ctx.fillStyle = LABEL_COLOR;
                        ctx.font = `${FONT_SIZE}px monospace`;
                        ctx.textAlign = "center";
                        ctx.textBaseline = "bottom";
                        ctx.fillText(t.time.toFixed(2) + "s", px, cy - THUMB_RADIUS - 2);
                    }

                    // ── Duration label (on the +/- button row) ───────────
                    const { plusX: dlPlusX, cy: dlCy } = getButtonBounds(this);
                    ctx.fillStyle = "#000";
                    ctx.font = `12px monospace`;
                    ctx.textAlign = "right";
                    ctx.textBaseline = "middle";
                    ctx.fillText("DURATION: "+ duration.toFixed(2) + "s", this.size[0] - TRACK_PADDING, dlCy);

                    ctx.restore();
                };

                // ── Mouse interaction ────────────────────────────────────
                node.onMouseDown = function (e, localPos) {
                    const { x: tx, y: ty, w: tw } = getTrackBounds(this);
                    const cy = ty + SLIDER_HEIGHT / 2;
                    const mx = localPos[0];
                    const my = localPos[1];

                    // Check +/- button clicks
                    const { minusX, plusX, btnY } = getButtonBounds(this);
                    
                    // Adds 5 pixels of "padding" to the hitbox in every direction
                    const inBtn = (bx) => mx >= bx - 5 && mx <= bx + BTN_SIZE + 5 &&
                        my >= btnY - 5 && my <= btnY + BTN_SIZE + 5;

                    console.log({
                        mouse: { mx, my },
                        bounds: { minusX, plusX, btnY, BTN_SIZE },
                        isOverMinus: inBtn(minusX),
                        isOverPlus: inBtn(plusX),
                        numActive
                    });
                    if (inBtn(minusX) && numActive > 1) {
                        numActive--;
                        serializeValue();
                        this.setDirtyCanvas(true, true);
                        return true;
                    }
                    if (inBtn(plusX) && numActive < MAX_SPLITS) {
                        numActive++;
                        serializeValue();
                        this.setDirtyCanvas(true, true);
                        return true;
                    }

                    for (let i = 0; i < MAX_SPLITS; i++) {
                        const px = timeToX(thumbs[i].time, tx, tw);
                        const dist = Math.sqrt((mx - px) ** 2 + (my - cy) ** 2);
                        if (dist <= THUMB_RADIUS + 2) {
                            dragIndex = i;
                            dragOffsetX = mx - px;
                            return true;
                        }
                    }
                    return false;
                };

                node.onMouseMove = function (e, localPos) {
                    if (dragIndex < 0) return false;
                    const { x: tx, w: tw } = getTrackBounds(this);
                    let newTime = xToTime(localPos[0] - dragOffsetX + tx + (thumbs[dragIndex].time / duration) * tw - timeToX(thumbs[dragIndex].time, tx, tw) + timeToX(thumbs[dragIndex].time, tx, tw), tx, tw);

                    // Cleaner: just map mouse X directly
                    newTime = xToTime(localPos[0], tx, tw);

                    // Enforce sorted order: clamp between neighbours
                    const minTime = dragIndex > 0 ? thumbs[dragIndex - 1].time + 0.001 : 0;
                    const maxTime = dragIndex < numActive - 1 ? thumbs[dragIndex + 1].time - 0.001 : duration;
                    thumbs[dragIndex].time = Math.max(minTime, Math.min(maxTime, newTime));

                    serializeValue();
                    this.setDirtyCanvas(true, true);
                    return true;
                };

                node.onMouseUp = function (e, localPos) {
                    if (dragIndex >= 0) {
                        dragIndex = -1;
                        return true;
                    }
                    return false;
                };

                function applyDuration(newDur) {
                    if (newDur > 0 && newDur !== duration) {
                        duration = newDur;
                        initThumbs();
                        node.setDirtyCanvas(true, true);
                    }
                }

                // onExecuted: Python sends real sample-accurate duration after Run.
                // This is the only reliable source — the Load Audio "duration" widget
                // is a trim setting (0 = full file), not the actual file length.
                const origExecuted = node.onExecuted;
                node.onExecuted = function (message) {
                    if (origExecuted) origExecuted.call(this, message);
                    if (message?.duration !== undefined) {
                        const raw = message.duration;
                        applyDuration(parseFloat(Array.isArray(raw) ? raw[0] : raw));
                    }
                };

                // Restore from serialized value if present
                if (valueWidget.value && valueWidget.value !== "[]") {
                    try {
                        const saved = JSON.parse(valueWidget.value);
                        if (Array.isArray(saved) && saved.length > 0) {
                            numActive = saved.length;
                            for (let i = 0; i < MAX_SPLITS; i++) {
                                thumbs[i] = { time: saved[i] ?? duration * (i + 1) / (MAX_SPLITS + 1) };
                            }
                            thumbs.sort((a, b) => a.time - b.time);
                        } else {
                            initThumbs();
                        }
                    } catch {
                        initThumbs();
                    }
                } else {
                    initThumbs();
                }

                // Ensure node is tall enough to show the slider
                const minH = 160;
                if (node.size[1] < minH) {
                    node.setSize([node.size[0], minH]);
                }

                node.setDirtyCanvas(true, true);

            }, 0);
        };
    }
});