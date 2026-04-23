import { app } from "../../scripts/app.js";

console.log("[TKLocateSpeakersUsingSilenceBreaks] JS LOADED");

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
const SPEAKER_TALK_COLOR = "rgba(247, 13, 13, 0.55)";   // semi-transparent green fill
const SPEAKER_TALK_BORDER = "#e0e7e7";                   // green border
const SILENCE_HALF_W_SEC = 0.15;                    // ±0.15s visual half-width around midpoint

app.registerExtension({
    name: "extTKLocateSpeakersUsingSilenceBreaks",

    async beforeRegisterNodeDef(nodeType, nodeData, _app) {
        if (nodeData.name !== "TKLocateSpeakersUsingSilenceBreaks") return;

        const orig = nodeType.prototype.onNodeCreated;

        nodeType.prototype.onNodeCreated = function () {
            if (orig) orig.apply(this, arguments);

            setTimeout(() => {
                const NUM_TRACKS = 14;
                const MAX_SPLITS = 20;
                const MIN_HEIGHT_FORM = 480;
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
                let speakerTimes = [];   // ← start,end,speaker

                const transitionWidget = node.widgets?.find(w => w.name === "speaker_times");
                if (transitionWidget) transitionWidget.hidden = true;

                // ── Geometry helpers ─────────────────────────────────────
               
                drawButtons(node);

              

                const callbackTrackDataChanged = (node) => {
                    const stateWidget = node.widgets.find(w => w.name === "track_state");

                    node.widgets.forEach(w => {
                        if (w.name?.startsWith("track_start_") || w.name?.startsWith("track_end_")) {
                            const oldCallback = w.callback;
                            w.callback = function (value) {
                                if (oldCallback) oldCallback.apply(this, arguments);

                                // Set the flag to dirty
                                if (stateWidget) stateWidget.value = "DataChange";
                                console.log("State set to: DataChange");
                            };
                        }
                    });
                };

                // Initialize the change listeners
                callbackTrackDataChanged(this);

                function clearTrackData(node) {
                    if (!node || !node.widgets) return;

                   
                    node.widgets.forEach(w => {
                        if (w.name?.startsWith("track_start_") || w.name?.startsWith("track_end_")) {
                            w.value = 0;
                            // Explicitly trigger the callback so the backend sees the reset
                            if (w.callback) w.callback.call(node, 0);
                        }
                    });

                    // Refresh custom UI drawing
                    if (typeof drawButtons === "function") {
                        drawButtons(node);
                    }

                    // Refresh the ComfyUI canvas
                    node.setDirtyCanvas(true, true);
                } 
             
                function populateEditBoxesUsingSpeakerTimes(node, segments) {
                    if (!node || !segments) return;

                    // 1. Call your existing clear function first
                    clearTrackData(node);

                    // 2. Sort by speaker ID, then by start time (chronological)
                    const sortedSegments = [...segments].sort((a, b) => {
                        if (a.speaker !== b.speaker) {
                            return String(a.speaker).localeCompare(String(b.speaker));
                        }
                        return a.start - b.start;
                    });

                    const MAX_PER_SPEAKER = NUM_TRACKS/2;
                    let currentSpeaker = null;
                    let currentCount = 0;
                    let columnOffset = 0;

                    // 3. Distribute into the correct slots
                    for (const seg of sortedSegments) {
                        if (currentSpeaker !== null && String(seg.speaker) !== String(currentSpeaker)) {
                            columnOffset += MAX_PER_SPEAKER;
                            currentCount = 0;
                            if (columnOffset >= NUM_TRACKS) break;
                        }

                        currentSpeaker = seg.speaker;
                        currentCount++;

                        if (currentCount <= MAX_PER_SPEAKER) {
                            const trackNum = columnOffset + currentCount;

                            const sW = node.widgets.find(w => w.name === `track_start_${trackNum}`);
                            const eW = node.widgets.find(w => w.name === `track_end_${trackNum}`);

                            if (sW) {
                                sW.value = parseFloat(seg.start || 0);
                                if (sW.callback) sW.callback.call(node, sW.value);
                            }
                            if (eW) {
                                eW.value = parseFloat(seg.end || 0);
                                if (eW.callback) eW.callback.call(node, eW.value);
                            }
                        }
                    }

                    if (typeof drawButtons === "function") drawButtons(node);
                    node.setDirtyCanvas(true, true);
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
                  
                    // ← add this guard
                    if (node.widgets.find(w => w.name === "footer_btns")) {
                        node.setDirtyCanvas(true, true);
                        return;
                    }


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
                    const HALF = NUM_TRACKS / 2; 
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

                    // --- CREATE DETECT BUTTON ---
                    const detectBtn = document.createElement("button");
                    detectBtn.textContent = "DETECT SPEAKERS - FROM AUDIO FILE";
                    detectBtn.style.cssText = `flex: 1; height: 26px; cursor: pointer; background: #224422; color: #fff; border: 1px solid #446644; border-radius: 4px; font-size: 11px;`;

                    detectBtn.onclick = async () => {
                        let audioPath = null;  // ← add this
                        console.log("detect button clicked!");  
                        const fullaudioInput = node.inputs?.find(i => i.name === "fullaudio");

                        if (!fullaudioInput?.link) {
                            console.error("No Load Audio node connected to fullaudio input!");
                            alert("Please connect a Load Audio node first!");
                            return;
                        }

                        const link = app.graph.links[fullaudioInput.link];
                        const sourceNode = app.graph.getNodeById(link.origin_id);
                        const audioWidget = sourceNode.widgets?.find(w => w.name === "audio");
                        audioPath = audioWidget?.value;

                        if (!audioPath) {
                            console.error("Load Audio node is connected but no file selected!");
                            alert("Please select an audio file in the Load Audio node!");
                            return;
                        }



                        detectBtn.textContent = "Detecting...";
                        detectBtn.disabled = true;

                        try {
                            // 1. First, find the widget's current value from the node
                            const thresholdWidget = node.widgets.find(w => w.name === "silence_threshold");
                            const currentThreshold = thresholdWidget ? thresholdWidget.value : 1.0; // Fallback to 1.0 if not found

                            const response = await fetch('/tk/detect_speakers', {
                                method: 'POST',
                                body: JSON.stringify({ audio: audioPath, silence_threshold: currentThreshold }), 
                                // Ensure this is a string
                                headers: { 'Content-Type': 'application/json' }
                            });
                         

                            const data = await response.json();

                            console.log("response status:", response.status);
                            console.log("response data:", data);

                            if (data.speaker_times) {
                                if (data.duration) {
                                    applyDuration(data.duration);
                                }
                                node.speakerTimes = data.speaker_times;
                                populateEditBoxesUsingSpeakerTimes(node, node.speakerTimes);
                                node.setDirtyCanvas(true, true);
                            }
                        } catch (err) {
                            console.error("Detection failed:", err);

                            detectBtn.textContent = "Detect Speakers";
                            detectBtn.disabled = false;
                        } finally {
                            detectBtn.textContent = "DETECT SPEAKERS - LOAD GRAPH";
                            detectBtn.disabled = false;
                        }
                    };




                    // --- CREATE CLEAR BUTTON ---
                    const clearBtn = document.createElement("button");
                    clearBtn.textContent = "Clear";
                    clearBtn.style.cssText = `flex: 1; height: 26px; cursor: pointer; background: #442222; color: #fff; border: 1px solid #664444; border-radius: 4px; font-size: 11px;`;

                    clearBtn.onclick = async () => {
                        clearTrackData(node);
                        node.speakerTimes = [];
                    }

                    // --- APPEND AND ADD WIDGET ---
                    footerBtnRow.appendChild(detectBtn);
                    footerBtnRow.appendChild(clearBtn);

                    node.addDOMWidget("footer_btns", "div", footerBtnRow, {
                        getValue() { return null; },
                        setValue() { },
                        getHeight() { return 40; },
                    });
                } // End of drawButtons

                
                

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
                function drawSpeakerSegments(ctx, segments, tx, tw, cy) {
                    if (!segments || segments.length === 0) return;

                    for (const segment of segments) {
                        // 1. Calculate positions
                        const x0 = timeToX(segment.start, tx, tw);
                        const x1 = timeToX(segment.end, tx, tw);

                        const blockW = Math.max(4, x1 - x0);
                        const blockH = 18; // slightly taller than the 6px track
                        const blockY = cy - blockH / 2;

                        // 2. Setup styles
                        ctx.beginPath();
                        ctx.roundRect(x0, blockY, blockW, blockH, 2);

                        // Blue for Speaker 0, Green for Speaker 1
                        ctx.fillStyle = (segment.speaker === 1) ? "#2ecc71" : "#3498db";

                        ctx.globalAlpha = 0.7;
                        ctx.fill();

                        // 3. Add a subtle border
                        ctx.strokeStyle = "rgba(255, 255, 255, 0.4)";
                        ctx.lineWidth = 1;
                        ctx.stroke();
                    }

                    // Reset alpha so it doesn't affect other drawing
                    ctx.globalAlpha = 1.0;
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
                    const cy = ty + 30; // Center the slider line

                   // --- FIX ENDS HERE ---


                    ctx.save();

                    // ── +/- buttons ──────────────────────────────────────
                    const { minusX, labelX, plusX, cy: bcy, btnY } = getButtonBounds(this);
 


                    // ── No duration yet ──────────────────────────────────
                    if (duration <= 0) {
                        ctx.fillStyle = "#fff";
                        ctx.font = `bold 14px sans-serif`;
                        // ADD THIS LINE
                        ctx.textAlign = "center";

                        // "middle" is usually better than "center" for textBaseline
                        ctx.textBaseline = "middle"; 
                        ctx.fillText("-- MAKE SURE AUDIO FOLLOWS RULES --", tx + tw / 2, cy);
                      
                        ctx.restore();
                        return;
                    }

                    // ── Track background ─────────────────────────────────
                    ctx.beginPath();
                    ctx.roundRect(tx, cy - 3, tw, 6, 3);
                    ctx.fillStyle = TRACK_BG;
                    ctx.fill();

                    
                    // Call our new helper function
                    // Pass 'this.speakerTimes' so it uses the data we saved
                    drawSpeakerSegments(ctx, this.speakerTimes, tx, tw, cy);

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
                    //ctx.fillText("DURATION: " + duration.toFixed(2) + "s", this.size[0] - TRACK_PADDING, dlCy);
                  

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

                    if (message?.speaker_times !== undefined) {
                        const raw = message.speaker_times;
                        console.log("speaker_times received:", raw);

                        // ── Fixed Processing Logic ──
                        // Just ensure it's an array and handle the ComfyUI "wrapped in array" quirk if needed
                        let data = Array.isArray(raw) ? raw : [];

                        // ComfyUI sometimes wraps the whole payload in another array [ [{...}, {...}] ]
                        if (data.length > 0 && Array.isArray(data[0])) {
                            data = data[0];
                        }

                        // Map the data, ensuring the numbers are parsed but the structure stays
                        speakerTimes = data.map(seg => ({
                            start: parseFloat(seg.start),
                            end: parseFloat(seg.end),
                            speaker: parseInt(seg.speaker)
                        })).filter(seg => !isNaN(seg.start) && !isNaN(seg.end));

                        console.log("[TKLocateSpeakers] speakerTimes after processing:", speakerTimes);
                        console.log("**** GOT SPEAKER TIMES *****");

                       
                        populateEditBoxesUsingSpeakerTimes(node, speakerTimes);


                        node.setDirtyCanvas(true, true);
                    } else {
                        console.log("[TKLocateSpeakers] speaker_times was NOT in message!");  // ← ADD THIS
                    }

                   

                    // Duration (unchanged)
                    if (message?.duration !== undefined) {
                        const raw = message.duration;
                        applyDuration(parseFloat(Array.isArray(raw) ? raw[0] : raw));
                    }

                    // ── Receive speaker segment objects from Python ──
                    if (message?.speaker_times !== undefined) {
                        const raw = message.speaker_times;

                        // 1. Map the objects correctly and ensure we have numbers
                        // 2. Attach it to 'this' so the canvas draw loop can find it
                        this.speakerTimes = (Array.isArray(raw) ? raw : []).map(seg => ({
                            start: parseFloat(seg.start),
                            end: parseFloat(seg.end),
                            speaker: parseInt(seg.speaker)
                        })).filter(seg => !isNaN(seg.start) && !isNaN(seg.end));

                        console.log("Speaker Data Processed:", this.speakerTimes);

                        // 3. Trigger a redraw
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

            },10); // set timeout
        }; // onNodCreated
    } // beforeRegistered
});