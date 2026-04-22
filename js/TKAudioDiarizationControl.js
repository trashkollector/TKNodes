import { app } from "../../scripts/app.js";

console.log("[TKAudioDiarizationControl] JS LOADED");

const SLIDER_HEIGHT = 28;
const TRACK_PADDING = 16;
const ACTIVE_COLOR = "#4a9eff";
const INACTIVE_COLOR = "#555";
const TRACK_BG = "#222";
const LABEL_COLOR = "#ccc";
const FONT_SIZE = 10;
const BTN_SIZE = 18;
const BTN_MARGIN = 6;

// ── Silence block appearance ──────────────────────────────────────────────────
const SILENCE_COLOR = "rgba(247, 13, 13, 0.55)";   // semi-transparent green fill
const SILENCE_BORDER = "#e0e7e7";                   // green border
const SILENCE_HALF_W_SEC = 0.15;                    // ±0.15s visual half-width around midpoint

app.registerExtension({
    name: "extTKAudioDiarizationControl",

    async beforeRegisterNodeDef(nodeType, nodeData, _app) {
        if (nodeData.name !== "TKAudioDiarizationControl") return;

        const orig = nodeType.prototype.onNodeCreated;

        nodeType.prototype.onNodeCreated = function () {
            if (orig) orig.apply(this, arguments);

            setTimeout(() => {
                const NUM_TRACKS = 10;
                const MAX_SPLITS = 20;
                const MIN_HEIGHT_FORM = 400;
                const BTN_ROW_H = 26;


                const node = this;


                const hideWidget = (w) => {
                    w.computeSize = () => [0, -4];
                    w.draw = () => { };
                    w.type = "converted-widget";
                };


                // ── State ────────────────────────────────────────────────
                let duration = 0;
                let numActive = 1;
                let dragIndex = -1;
                let dragOffsetX = 0;
                let transitionTimes = [];   // ← NEW: midpoints in seconds

                const transitionWidget = node.widgets?.find(w => w.name === "transition_times");
                if (transitionWidget) transitionWidget.hidden = true;

                // ── Geometry helpers ─────────────────────────────────────
               
                drawButtons(node);
                 
                function populateFromTransitions(node, transitions) {
                    if (!node || !transitions || transitions.length === 0) return;

                    // 1. Reset all widgets to 0 first for a clean slate
                    node.widgets.forEach(w => {
                        if (w.name?.startsWith("track_")) w.value = 0;
                    });

                    let lastTime = 0;
                    const HALF = NUM_TRACKS / 2; // Assuming 5

                    for (let i = 0; i < transitions.length; i++) {
                        const currentTime = transitions[i];

                        // Calculate which track number we are on (1, 2, 3...)
                        // Since we use 2 speakers per "step", track index is floor(i/2) + 1
                        const trackNum = Math.floor(i / 2) + 1;

                        // Stop if we run out of available UI tracks
                        if (trackNum > HALF) break;

                        // Alternating logic: 
                        // i = 0, 2, 4... -> Speaker 1 (Start/End i)
                        // i = 1, 3, 5... -> Speaker 2 (Start/End j)
                        const isSpeakerOne = (i % 2 === 0);

                        if (isSpeakerOne) {
                            // Assign to Speaker 1
                            const startW = node.widgets.find(w => w.name === `track_start_${trackNum}`);
                            const endW = node.widgets.find(w => w.name === `track_end_${trackNum}`);
                            if (startW) startW.value = lastTime;
                            if (endW) endW.value = currentTime;
                        } else {
                            // Assign to Speaker 2 (The "j" tracks in your grid)
                            const trackNumJ = trackNum + HALF;
                            const startW = node.widgets.find(w => w.name === `track_start_${trackNumJ}`);
                            const endW = node.widgets.find(w => w.name === `track_end_${trackNumJ}`);
                            if (startW) startW.value = lastTime;
                            if (endW) endW.value = currentTime;
                        }

                        lastTime = currentTime;
                    }

                    // 2. Refresh the UI to show the new numbers
                    drawButtons(node);
                }

                function clearCustomWidgets(node) {
                    if (!node || !node.widgets) return;

                    // Loop backwards to safely remove items from the array
                    for (let i = node.widgets.length - 1; i >= 0; i--) {
                        const w = node.widgets[i];

                        // Target all the custom widgets we created
                        if (w.name === "timeline_spacer" ||
                            w.name === "track_controls_group" ||
                            w.name === "track_footer") {

                            // 1. Physically remove the HTML element from the browser
                            if (w.element) {
                                w.element.remove();
                            }

                            // 2. Remove the widget object from ComfyUI's internal list
                            node.widgets.splice(i, 1);
                        }
                    }
                }

                function clearCustomWidgets(node) {
                    if (!node || !node.widgets) return;

                    for (let i = node.widgets.length - 1; i >= 0; i--) {
                        const w = node.widgets[i];

                        // Add the wildcard check for "track_row_" and "track_controls_group"
                        if (w.name === "timeline_spacer" ||
                            w.name === "track_footer" ||
                            w.name === "track_controls_group" ||
                            (w.name && w.name.startsWith("track_row_"))) { // <--- ADD THIS

                            if (w.element) w.element.remove();
                            node.widgets.splice(i, 1);
                        }
                    }
                }


                function drawButtons(node) {
                    if (!node || !node.widgets) return;

   
                    clearCustomWidgets(node);

                    // 1. Create a spacer DIV and make it a flexbox
                    const timelineSpacer = document.createElement("div");
                    timelineSpacer.style.cssText = `
                        height: 60px; 
                        display: flex; 
                        align-items: flex-end; /* Pushes labels to the bottom of the 60px */
                        padding-bottom: 5px;   /* Small gap above the buttons */
                        box-sizing: border-box;
                    `;

                    const leftLabel = document.createElement("span");
                    leftLabel.textContent = "SPEAKER ONE";
                    leftLabel.style.cssText = `font-size: 11px; font-weight: bold; color: #fff; flex: 1; text-align: center;`;

                    const rightLabel = document.createElement("span");
                    rightLabel.textContent = "SPEAKER TWO";
                    rightLabel.style.cssText = `font-size: 11px; font-weight: bold; color: #fff; flex: 1; text-align: center;`;

                    // 2. Append labels TO the spacer
                    timelineSpacer.appendChild(leftLabel);
                    timelineSpacer.appendChild(rightLabel);
                    // 2. Add the spacer as the FIRST widget
                    node.addDOMWidget("timeline_spacer", "div", timelineSpacer, {
                        getHeight() { return 60; },
                        getValue() { return null; },
                        setValue() { },
                    });

                    // ... Then continue with your scrollContainer and button logic below ...
                    const scrollContainer = document.createElement("div");

                    const makeSliderField = (label, widget) => {
                        const wrap = document.createElement("div");
                        wrap.style.cssText = `
                             flex: 1;
                            display: flex;
                            align-items: center;
                            gap: 4px;
                            background: #2a2a2a;
                            border: 1px solid #444;
                            border-radius: 4px;
                            padding: 1px 4px;  /* ← was 3px 6px */
                            min-width: 0;
                            height: 22px;      /* ← constrain height */
                            box-sizing: border-box;
                        `;

                        const lbl = document.createElement("span");
                        lbl.textContent = label;
                        lbl.style.cssText = `font-size: 10px; color: #aaa; white-space: nowrap; flex-shrink: 0;`;

                        const input = document.createElement("input");
                        input.type = "number";
                        input.value = widget.value ?? 0;
                        input.step = "0.1";
                        input.style.cssText = `flex: 1; min-width: 0; background: transparent; border: none; color: #fff; font-size: 12px; text-align: right; outline: none;`;
                        input.min = "0";      // Minimum limit
                        input.max = "300";    // Maximum limit

                        input.addEventListener("input", () => {
                            widget.value = parseFloat(input.value) || 0;
                        });
                        widget.callback = () => { input.value = widget.value; };

                        wrap.appendChild(lbl);
                        wrap.appendChild(input);
                        return wrap;
                    };

                    // Hide ALL track widgets first
                    for (let i = 1; i <= NUM_TRACKS; i++) {
                        const startW = node.widgets.find(w => w.name === `track_start_${i}`);
                        const endW = node.widgets.find(w => w.name === `track_end_${i}`);
                        if (startW) hideWidget(startW);
                        if (endW) hideWidget(endW);
                    }

                    // Build 4-column rows: [start_i, end_i, start_i+HALF, end_i+HALF]
                    const HALF = NUM_TRACKS / 2; // 5
                    for (let i = 1; i <= HALF; i++) {
                        const j = i + HALF;

                        const startW_i = node.widgets.find(w => w.name === `track_start_${i}`);
                        const endW_i = node.widgets.find(w => w.name === `track_end_${i}`);
                        const startW_j = node.widgets.find(w => w.name === `track_start_${j}`);
                        const endW_j = node.widgets.find(w => w.name === `track_end_${j}`);

                        const row = document.createElement("div");
                        row.style.cssText = `display: flex; gap: 6px; width: 100%; align-items: center; box-sizing: border-box; padding: 1px 0;`;

                        if (startW_i) row.appendChild(makeSliderField(`start_${i}`, startW_i));
                        if (endW_i) row.appendChild(makeSliderField(`end_${i}`, endW_i));
                        if (startW_j) row.appendChild(makeSliderField(`start_${j}`, startW_j));
                        if (endW_j) row.appendChild(makeSliderField(`end_${j}`, endW_j));

                        node.addDOMWidget(`track_row_${i}`, "div", row, {
                            getValue() { return null; },
                            setValue() { },
                            getHeight() { return 28; },
                            computeSize() { return [0, 28]; }, // ← add this
                        });
                    }


                    // 2. NOW ADD THE BUTTONS (After the tracks)
                    const footerBtnRow = document.createElement("div");
                    footerBtnRow.style.cssText = `
                        display: flex; 
                        gap: 8px; 
                        padding: 8px 4px; 
                        width: 100%; 
                        box-sizing: border-box;
                    `;

                    const clearBtn = document.createElement("button");
                    clearBtn.textContent = "Clear";
                    clearBtn.style.cssText = `flex: 1; height: 26px; cursor: pointer; background: #442222; color: #fff; border: 1px solid #664444; border-radius: 4px; font-size: 11px;`;
                    clearBtn.onclick = () => {
                        // Loop through all track widgets and reset to 0
                        node.widgets.forEach(w => {
                            if (w.name?.startsWith("track_start_") || w.name?.startsWith("track_end_")) {
                                w.value = 0;
                            }
                        });
                        drawButtons(node); // Redraw to update the text boxes
                    };

                    const loadBtn = document.createElement("button");
                    loadBtn.textContent = "Populate edit boxs with Diarization data";
                    loadBtn.style.cssText = `flex: 2; height: 26px; cursor: pointer; background: #223344; color: #fff; border: 1px solid #334455; border-radius: 4px; font-size: 11px;`;
                    // 2. Update your button onclick (inside drawButtons)
                    loadBtn.onclick = () => {
                        const data = transitionTimes;

                        if (!data || data.length === 0) {
                            alert("No diarization data found. Please run the node first.");
                            return;
                        }

                        // 2. Run the population logic
                        populateFromTransitions(node, data);
                    }
                    footerBtnRow.appendChild(clearBtn);
                    footerBtnRow.appendChild(loadBtn);

                    node.addDOMWidget("track_footer", "div", footerBtnRow, {
                        getHeight() { return 40; }
                    });

                    // 3. FINALLY, set the height
                    node.setSize([node.size[0], MIN_HEIGHT_FORM]);
                    node.setDirtyCanvas(true, true);

                }
                
                

                function getButtonBounds(node) {
                    const rowY = node.size[1] - SLIDER_HEIGHT - BTN_ROW_H - 18;
                    const cy = rowY + BTN_ROW_H / 2;
                    const totalW = BTN_SIZE * 2 + BTN_MARGIN * 2 + 28;
                    const startX = (node.size[0] - totalW) / 2;
                    const minusX = startX;
                    const labelX = minusX + BTN_SIZE + BTN_MARGIN;
                    const plusX = labelX + 28 + BTN_MARGIN;
                    return { minusX, labelX, plusX, cy, btnY: cy - BTN_SIZE / 2 };
                }

                function getTrackBounds(node) {
                    const x = TRACK_PADDING;
                    const w = node.size[0] - TRACK_PADDING * 2;
                    const y = node.widgets[node.widgets.length - 1].last_y + 40;
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

                    //const { x: tx, y: ty, w: tw } = getTrackBounds(this);
                    //const cy = ty + SLIDER_HEIGHT / 2;
                    // --- FIX STARTS HERE ---
                    const { x: tx, w: tw } = getTrackBounds(this);
                    const ty = 100; // Hard-code this to stay at the top (within your 60-80px padding)
                    const cy = ty + 10; // Center the slider line

                   // --- FIX ENDS HERE ---


                    ctx.save();

                    // ── +/- buttons ──────────────────────────────────────
                    const { minusX, labelX, plusX, cy: bcy, btnY } = getButtonBounds(this);
 


                    // ── No duration yet ──────────────────────────────────
                    if (duration <= 0) {
                        ctx.fillStyle = "#000";
                        ctx.font = `14px sans-serif`;
                        ctx.textAlign = "center";
                        ctx.textBaseline = "middle";
                        ctx.fillText("--Connect then RUN to load Diarization - Requires clean audio to work perfectly --", tx + tw / 2, cy);
                      
                        ctx.restore();
                        return;
                    }

                    // ── Track background ─────────────────────────────────
                    ctx.beginPath();
                    ctx.roundRect(tx, cy - 3, tw, 6, 3);
                    ctx.fillStyle = TRACK_BG;
                    ctx.fill();

                    // ── Silence blocks (drawn ON the track, behind thumbs) ──
                    if (transitionTimes.length > 0) {
                        for (const midSec of transitionTimes) {
                            const x0 = timeToX(Math.max(0, midSec - SILENCE_HALF_W_SEC), tx, tw);
                            const x1 = timeToX(Math.min(duration, midSec + SILENCE_HALF_W_SEC), tx, tw);
                            const blockW = Math.max(4, x1 - x0);  // at least 4px wide so it's always visible
                            const blockH = 18;                      // slightly taller than the 6px track
                            const blockY = cy - blockH / 2;

                            ctx.beginPath();
                            ctx.roundRect(x0, blockY, blockW, blockH, 2);
                            ctx.fillStyle = SILENCE_COLOR;
                            ctx.fill();
                            ctx.strokeStyle = SILENCE_BORDER;
                            ctx.lineWidth = 1;
                            ctx.stroke();
                        }
                    }

                    // ── Tick marks ───────────────────────────────────────
                    const pxPerSec = tw / duration;
                    const totalSecs = Math.floor(duration);
                    for (let i = 0; i <= totalSecs; i++) {
                        const px = timeToX(i, tx, tw);
                        const isFive = (i % 5 === 0);
                        const tickH = isFive ? 7 : 4;
                        ctx.beginPath();
                        ctx.moveTo(px, cy + 4);
                        ctx.lineTo(px, cy + 4 + tickH);
                        ctx.strokeStyle = isFive ? "#000" : "#000000";
                        ctx.lineWidth = isFive ? 1 : 0.5;
                        ctx.stroke();
                        if (isFive && i > 0 && i < duration && pxPerSec * 5 > 24) {
                            ctx.fillStyle = "#000";
                            ctx.font = `8px monospace`;
                            ctx.textAlign = "center";
                            ctx.textBaseline = "top";
                            ctx.fillText(i + "s", px, cy + 13);
                        }
                    }

                  

                    // ── Duration label ───────────────────────────────────
                    const { plusX: dlPlusX, cy: dlCy } = getButtonBounds(this);
                    ctx.fillStyle = "#000";
                    ctx.font = `12px monospace`;
                    ctx.textAlign = "right";
                    ctx.textBaseline = "middle";
                    ctx.fillText("DURATION: " + duration.toFixed(2) + "s", this.size[0] - TRACK_PADDING, dlCy);
                  

                    ctx.restore();
                };

                // ── Mouse interaction ────────────────────────────────────
                node.onMouseDown = function (e, localPos) {
                    const { x: tx, y: ty, w: tw } = getTrackBounds(this);
                    const cy = ty + SLIDER_HEIGHT / 2;
                    const mx = localPos[0];
                    const my = localPos[1];

                                
                    return false;
                };



                function applyDuration(newDur) {
                    if (newDur > 0 && newDur !== duration) {
                        duration = newDur;
                        node.setDirtyCanvas(true, true);
                    }
                }

                // ── onExecuted: receive duration + silence_times from Python ──
                const origExecuted = node.onExecuted;
                node.onExecuted = function (message) {
                    if (origExecuted) origExecuted.call(this, message);

                    console.log("[TKSPTransition] Full message received:", JSON.stringify(message));  // ← ADD THIS

                    if (message?.duration !== undefined) {
                        const raw = message.duration;
                        applyDuration(parseFloat(Array.isArray(raw) ? raw[0] : raw));
                    }

                    if (message?.transition_times !== undefined) {
                        const raw = message.transition_times;
                        console.log("transition_times received:", raw);  // ← ADD THIS
                        transitionTimes = (Array.isArray(raw) ? raw : [])
                            .map(v => parseFloat(Array.isArray(v) ? v[0] : v))
                            .filter(v => !isNaN(v) && v >= 0);
                        console.log("[TKTransition] transitionTimes after processing:", transitionTimes);  // ← ADD THIS

                        console.log("****TRANSITIONS*****");
                        
                        node.widgets.forEach(w => {
                            if (w.name?.startsWith("track_start_") || w.name?.startsWith("track_end_")) {
                                w.value = 0;
                            }
                        });
                       
                        populateFromTransitions(node, transitionTimes);


                        node.setDirtyCanvas(true, true);
                    } else {
                        console.log("[TKTransition] transition_times was NOT in message!");  // ← ADD THIS
                    }

                   

                    // Duration (unchanged)
                    if (message?.duration !== undefined) {
                        const raw = message.duration;
                        applyDuration(parseFloat(Array.isArray(raw) ? raw[0] : raw));
                    }

                    // ← NEW: silence midpoints in seconds
                    if (message?.transition_times !== undefined) {
                        const raw = message.transition_times;
                        transitionTimes = (Array.isArray(raw) ? raw : [])
                            .map(v => parseFloat(Array.isArray(v) ? v[0] : v))
                            .filter(v => !isNaN(v) && v >= 0);
                        node.setDirtyCanvas(true, true);
                    }


               

                };

               

                
                if (node.size[1] < MIN_HEIGHT_FORM) {
                    node.setSize([node.size[0], MIN_HEIGHT_FORM]);
                }

                // 🔒 lock height, allow width
                node.onResize = function (size) {
                    // keep whatever width user drags to
                    this.size[0] = size[0];
                    // but force height to our minH
                    this.size[1] = MIN_HEIGHT_FORM;
                };


                node.setDirtyCanvas(true, true);

            }, 0); // set timeout
        }; // onNodCreated
    } // beforeRegistered
});