import { app } from "../../scripts/app.js";

console.log("[TKAudio] JS LOADED");

app.registerExtension({
    name: "extTKAudioSpeakerTalkTime",

    async beforeRegisterNodeDef(nodeType, nodeData, _app) {
        if (nodeData.name !== "TKAudioSpeakerTalkTime") return;

        const orig = nodeType.prototype.onNodeCreated;

        nodeType.prototype.onNodeCreated = function () {
            if (orig) orig.apply(this, arguments);

            setTimeout(() => {
                const NUM_TRACKS = 5;

                const hideWidget = (w) => {
                    w.computeSize = () => [0, -4];
                    w.draw = () => { };
                    w.type = "converted-widget";
                };




                for (let i = 1; i <= NUM_TRACKS; i++) {
                    const startW = this.widgets?.find(w => w.name === `track_start_${i}`);
                    const endW = this.widgets?.find(w => w.name === `track_end_${i}`);

                    if (!startW || !endW) continue;


                    hideWidget(startW);
                    hideWidget(endW);

                    // Hide originals from drawing (keep them for serialization)
                    startW.type = "hidden";
                    endW.type = "hidden";

                    // Build the side-by-side row
                    const row = document.createElement("div");
                    row.style.cssText = `
                        display: flex;
                        gap: 6px;
                        width: 100%;
                        align-items: center;
                        box-sizing: border-box;
                        padding: 1px 0;
                    `;

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
                            padding: 3px 6px;
                            min-width: 0;
                        `;

                        const lbl = document.createElement("span");
                        lbl.textContent = label;
                        lbl.style.cssText = `
                            font-size: 10px;
                            color: #aaa;
                            white-space: nowrap;
                            flex-shrink: 0;
                        `;

                        const input = document.createElement("input");
                        input.type = "number";
                        input.value = widget.value ?? 0;
                        input.step = "0.1";
                        input.style.cssText = `
                            flex: 1;
                            min-width: 0;
                            background: transparent;
                            border: none;
                            color: #fff;
                            font-size: 12px;
                            text-align: right;
                            outline: none;
                        `;

                        input.addEventListener("input", () => {
                            widget.value = parseFloat(input.value) || 0;
                        });

                        // Also keep UI in sync if widget value changes externally
                        const origSerialize = widget.serializeValue;
                        widget.callback = () => { input.value = widget.value; };

                        wrap.appendChild(lbl);
                        wrap.appendChild(input);
                        return wrap;
                    };

                    row.appendChild(makeSliderField(`start_${i}`, startW));
                    row.appendChild(makeSliderField(`end_${i}`, endW));

                    this.addDOMWidget(`track_row_${i}`, "div", row, {
                        getValue() { return null; },
                        setValue() { },
                        getHeight() { return 28; },
                    });
                }

                this.setSize(this.computeSize());
                this.setDirtyCanvas(true, true);

            }, 0);
        };
    }
});