import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

console.log("[TKMultiImageSelect] JS LOADED");

app.registerExtension({
    name: "extTKMultiImageSelect",
    canvasOnly: true,  // tells Node 2.0 to skip this extension, uses legacy canvas rendering

    async beforeRegisterNodeDef(nodeType, nodeData, _app) {
        if (nodeData.name !== "TKMultiImageSelect") return;

        const orig = nodeType.prototype.onNodeCreated;
        const origOnDragDrop = nodeType.prototype.onDragDrop;

        nodeType.prototype.onDragDrop = function (e) {
            e.preventDefault();
            e.stopPropagation();
            // Prevent LiteGraph's default behavior from ever populating
            // node.imgs (which triggers the big bottom-of-node preview).
            this.imgs = null;
            return true;
        };

        nodeType.prototype.onNodeCreated = function () {
            if (orig) orig.apply(this, arguments);

            const node = this;

            setTimeout(() => {
                const NUM_SLOTS = 4;
                const NUM_COLS = 3;

                // store refs so clear/update can reach every slot later
                node.tkSlots = []; // [{ imageW, thumb, placeholder }, ...]

                const hideWidget = (w) => {
                    w.computeSize = () => [0, -4];
                    w.draw = () => { };
                    w.type = "hidden";
                };

                const uploadFile = async (file) => {
                    const formData = new FormData();
                    formData.append("image", file, file.name);
                    formData.append("type", "input");
                    formData.append("overwrite", "true");

                    const resp = await api.fetchApi("/upload/image", {
                        method: "POST",
                        body: formData,
                    });

                    if (resp.status !== 200) {
                        console.error("[TKMultiImageSelect] upload failed", resp.status, resp.statusText);
                        return null;
                    }
                    return await resp.json(); // { name, subfolder, type }
                };

                const previewUrl = (name, subfolder = "") => {
                    return api.apiURL(
                        `/view?filename=${encodeURIComponent(name)}&type=input&subfolder=${encodeURIComponent(subfolder)}`
                    );
                };

                // ---- Single source of truth for "widget value -> what's drawn" ----
                // Call this any time an imageW.value changes (upload, drop, clear).
                const setSlotImage = (slot, fullName, subfolder = "") => {
                    const { imageW, thumb, placeholder } = slot;

                    if (imageW.options?.values && fullName && !imageW.options.values.includes(fullName)) {
                        imageW.options.values.push(fullName);
                    }
                    imageW.value = fullName || "";

                    if (fullName) {
                        thumb.src = previewUrl(fullName, subfolder);
                        thumb.style.display = "block";
                        placeholder.style.display = "none";
                    } else {
                        thumb.src = "";
                        thumb.style.display = "none";
                        placeholder.style.display = "flex";
                    }
                };

                // Redraws every slot from its current imageW.value.
                // Call after any bulk change (e.g. Clear All).
                const updateGrid = () => {
                    for (const slot of node.tkSlots) {
                        setSlotImage(slot, slot.imageW.value, "");
                    }
                    node.setDirtyCanvas(true, true);
                };
                node.updateGrid = updateGrid; // expose on the node in case you need it elsewhere

                // ---- Build the grid ----
                const buildGrid = () => {
                    let imageNum = 1;
                    for (let rowNum = 0; rowNum < NUM_SLOTS; rowNum++) {

                        const row = document.createElement("div");
                        row.style.cssText = `
                                display: flex;
                                gap: 6px;
                                width: 100%;
                                align-items: stretch;
                                box-sizing: border-box;
                                padding: 3px 0;
                            `;

                        for (let colNum = 0; colNum < NUM_COLS; colNum++) {

                            const imageW = node.widgets?.find(w => w.name === `image_${imageNum}`);
                            const slotIndex = imageNum;
                            imageNum++;

                            if (!imageW) continue;

                            hideWidget(imageW);

                            const imgBlock = document.createElement("div");
                            imgBlock.style.cssText = `
                                    display: flex;
                                    flex-direction: column;
                                    align-items: center;
                                    gap: 4px;
                                    background: #2a2a2a;
                                    border: 1px solid #444;
                                    border-radius: 4px;
                                    padding: 5px;
                                    width: 136px;
                                    flex-shrink: 0;
                                    box-sizing: border-box;
                                `;

                            const thumb = document.createElement("img");
                            thumb.style.cssText = `
                                    width: 124px;
                                    height: 124px;
                                    object-fit: contain;
                                    border-radius: 3px;
                                    background: #1a1a1a;
                                    display: ${imageW.value ? "block" : "none"};
                                `;
                            if (imageW.value) {
                                thumb.src = previewUrl(imageW.value);
                            }

                            const placeholder = document.createElement("div");
                            placeholder.textContent = `#${slotIndex}`;
                            placeholder.style.cssText = `
                                    width: 124px;
                                    height: 124px;
                                    display: ${imageW.value ? "none" : "flex"};
                                    align-items: center;
                                    justify-content: center;
                                    color: #666;
                                    font-size: 13px;
                                    background: #1a1a1a;
                                    border-radius: 3px;
                                `;

                            const uploadBtn = document.createElement("button");
                            uploadBtn.textContent = "browse";
                            uploadBtn.style.cssText = `
                                    width: 100%;
                                    font-size: 10px;
                                    padding: 2px 0;
                                    background: #3a3a3a;
                                    border: 1px solid #555;
                                    border-radius: 3px;
                                    color: #ddd;
                                    cursor: pointer;
                                `;

                            const fileInput = document.createElement("input");
                            fileInput.type = "file";
                            fileInput.accept = "image/*";
                            fileInput.style.display = "none";

                            // register this slot so clear/update can reach it
                            const slot = { imageW, thumb, placeholder };
                            node.tkSlots.push(slot);

                            fileInput.addEventListener("change", async () => {
                                const file = fileInput.files?.[0];
                                if (!file) return;

                                const result = await uploadFile(file);
                                if (!result) return;

                                const fullName = result.subfolder
                                    ? `${result.subfolder}/${result.name}`
                                    : result.name;

                                setSlotImage(slot, fullName, result.subfolder);
                                node.setDirtyCanvas(true, true);
                            });

                            uploadBtn.addEventListener("click", () => fileInput.click());

                            imgBlock.appendChild(thumb);
                            imgBlock.appendChild(placeholder);
                            imgBlock.appendChild(uploadBtn);
                            imgBlock.appendChild(fileInput);

                            //// DRAG AND DROP

                            imgBlock.addEventListener("dragover", (e) => {
                                e.preventDefault();
                                e.stopPropagation();
                                imgBlock.style.borderColor = "#888";
                            });

                            imgBlock.addEventListener("dragleave", (e) => {
                                e.preventDefault();
                                e.stopPropagation();
                                imgBlock.style.borderColor = "#444";
                            });

                            imgBlock.addEventListener("drop", async (e) => {
                                e.preventDefault();
                                e.stopPropagation();
                                imgBlock.style.borderColor = "#444";

                                const file = e.dataTransfer?.files?.[0];
                                if (!file || !file.type.startsWith("image/")) return;

                                const result = await uploadFile(file);
                                if (!result) return;

                                const fullName = result.subfolder
                                    ? `${result.subfolder}/${result.name}`
                                    : result.name;

                                setSlotImage(slot, fullName, result.subfolder);
                                node.setDirtyCanvas(true, true);
                            });
                            /////////////////////

                            row.appendChild(imgBlock);

                        } //for cols

                        node.addDOMWidget(`row_${rowNum}`, "div", row, {
                            getValue() { return null; },
                            setValue() { },
                            getHeight() { return 162; },
                        });
                    } // for rows
                };

                buildGrid();

                // ---- Clear All button ----
                const clearBtn = document.createElement("button");
                clearBtn.textContent = "Clear All";
                clearBtn.style.cssText = `
                    width: 100%;
                    font-size: 14px;
                    padding: 2px 0;
                    background: #3a3a3a;
                    border: 1px solid #555;
                    border-radius: 3px;
                    color: #ddd;
                    cursor: pointer;
                `;
                clearBtn.onclick = () => {
                    for (const slot of node.tkSlots) {
                        setSlotImage(slot, "", "");
                    }
                    updateGrid();
                };

                node.addDOMWidget(`clear_button`, "div", clearBtn, {
                    getValue() { return null; },
                    setValue() { },
                    getHeight() { return 44; },
                });


                // Widen the default so prompts have room without needing a
                // manual resize. This only GROWS the node if it's currently
                // smaller than this minimum — it never shrinks or overwrites
                // a size you already resized to (or one restored from a
                // saved workflow). Previously this called
                // this.setSize(this.computeSize()) unconditionally, which
                // silently wiped out manual resizes on every reload because
                // computeSize() has no idea how wide you want the DOM rows.
                const MIN_WIDTH = 450;
                const MIN_HEIGHT = NUM_SLOTS * 162 + 70;

                const currentSize = this.size || [0, 0];
                this.setSize([
                    Math.max(currentSize[0], MIN_WIDTH),
                    Math.max(currentSize[1], MIN_HEIGHT),
                ]);
                this.setDirtyCanvas(true, true);

            }, 0);
        };
    }
});
