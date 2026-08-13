import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

console.log("[TKMultiImagePrompt] JS LOADED");

app.registerExtension({
    name: "extTKMultiImagePrompt",
    canvasOnly: true,  // tells Node 2.0 to skip this extension, uses legacy canvas rendering

    async beforeRegisterNodeDef(nodeType, nodeData, _app) {
        if (nodeData.name !== "TKMultiImagePrompt") return;

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

                node.tkSlots = []; // [{ imageW, thumb, placeholder, promptW, textarea }, ...]

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
                        console.error("[TKMultiImagePrompt] upload failed", resp.status, resp.statusText);
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

                const setSlotPrompt = (slot, text) => {
                    const { promptW, textarea } = slot;
                    promptW.value = text || "";
                    textarea.value = promptW.value;
                };

                const updateGrid = () => {
                    for (const slot of node.tkSlots) {
                        setSlotImage(slot, slot.imageW.value, "");
                        setSlotPrompt(slot, slot.promptW.value);
                    }
                    node.setDirtyCanvas(true, true);
                };
                node.updateGrid = updateGrid;

                // ---- Build rows ----
                for (let i = 1; i <= NUM_SLOTS; i++) {
                    const imageW = node.widgets?.find(w => w.name === `image_${i}`);
                    const promptW = node.widgets?.find(w => w.name === `prompt_${i}`);

                    if (!imageW || !promptW) continue;

                    hideWidget(imageW);
                    hideWidget(promptW);

                    // ---- Build the row ----
                    const row = document.createElement("div");
                    row.style.cssText = `
                display: flex;
                gap: 6px;
                width: 100%;
                align-items: stretch;
                box-sizing: border-box;
                padding: 3px 0;
            `;

                    // Thumbnail + upload button block
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
                    placeholder.textContent = `#${i}`;
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

                    // Prompt textarea block
                    const promptWrap = document.createElement("div");
                    promptWrap.style.cssText = `
                flex: 1;
                display: flex;
                min-width: 0;
            `;

                    const textarea = document.createElement("textarea");
                    textarea.value = promptW.value ?? "";
                    textarea.placeholder = `prompt_${i}`;
                    textarea.style.cssText = `
                flex: 1;
                min-width: 0;
                min-height: 150px;
                resize: vertical;
                background: #2a2a2a;
                border: 1px solid #444;
                border-radius: 4px;
                color: #fff;
                font-size: 11px;
                padding: 4px 6px;
                box-sizing: border-box;
                outline: none;
            `;

                    // register this slot so clear/update can reach it
                    const slot = { imageW, thumb, placeholder, promptW, textarea };
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

                    textarea.addEventListener("input", () => {
                        promptW.value = textarea.value;
                    });

                    // Keep UI in sync if widget value changes externally
                    promptW.callback = () => { textarea.value = promptW.value; };

                    promptWrap.appendChild(textarea);

                    row.appendChild(imgBlock);
                    row.appendChild(promptWrap);

                    node.addDOMWidget(`row_${i}`, "div", row, {
                        getValue() { return null; },
                        setValue() { },
                        getHeight() { return 162; },
                    });
                }

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
                        setSlotPrompt(slot, "");
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
                // saved workflow).
                const MIN_WIDTH = 560;
                const MIN_HEIGHT = NUM_SLOTS * 162 + 40;

                const currentSize = node.size || [0, 0];
                node.setSize([
                    Math.max(currentSize[0], MIN_WIDTH),
                    Math.max(currentSize[1], MIN_HEIGHT),
                ]);
                node.setDirtyCanvas(true, true);

            }, 0);
        }; // end node created
    }
});
