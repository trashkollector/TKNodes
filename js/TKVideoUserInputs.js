
import { app } from "../../scripts/app.js";
import { createModuleLogger } from "./utils/LoggerUtils.js";


// Initialize logger for this module
const log = createModuleLogger('TKVideoUserInputs');

class TKVideoUserInputsCanvas {
    constructor(node) {
        this.node = node;
        
        // Initialize properties
        this.node.properties = this.node.properties || {};
        this.initializeProperties();
        
        // Internal state
        this.node.intpos = { x: 0.5, y: 0.5 };
        this.node.capture = false;
        this.node.configured = false;
        
        // UI state
        this.hoverElement = null;
        this.scrollOffset = 0;
        this.dropdownOpen = null;
        
        // Collapsible sections state will be initialized after properties are set
        this.collapsedSections = {};
        
        // Custom input dialog state
        this.customInputDialog = null;
        this.inputDialogActive = false;
        
        // Tooltip state
        this.tooltipElement = null;
        this.tooltipTimer = null;
        this.tooltipDelay = 500; // ms - reduced for faster response
        this.showTooltip = false;
        this.tooltipMousePos = null; // Current mouse position
        
        // Auto-detect state
        this.detectedDimensions = null;
        this.dimensionCheckInterval = null;
        this.manuallySetByAutoFit = false;
        
        // Control positions (will be calculated dynamically)
        this.controls = {};


        this.icons = {};

        
       
       
        
        this.setupNode();
    }
    
    ensureMinimumSize() {
        if (this.node.size[0] < 120) {
            this.node.size[0] = 230;
        }
        
        // Calculate needed height based on current content
        const neededHeight = this.calculateNeededHeight();
        if (neededHeight > 0) {
            this.node.size[1] = Math.max(neededHeight, this.node.min_size[1]);
        } else {
            // Fallback to minimum if calculation not available
            if (this.node.size[1] < this.node.min_size[1]) {
                this.node.size[1] = this.node.min_size[1];
            }
        }
		
    }
    
    calculateNeededHeight() {
        const props = this.node.properties;
        if (!props || props.mode !== "Manual") return 0;
        
        let currentY = LiteGraph.NODE_TITLE_HEIGHT + 2;
        const spacing = 8;
        
        // Canvas height
        const canvasHeight = 320;
        currentY += canvasHeight + spacing;
        
        // Info text
        currentY += 15 + spacing;
        

        
        return currentY + 20; // Add bottom padding
    }
	
	
    
    initializeProperties() {
        const defaultProperties = {
            mode: "Manual",
            valueX: 1280,
            valueY: 1280,
            canvas_min_x: 200,
            canvas_max_x: 1280,
            canvas_step_x: 32,
            canvas_min_y: 200,
            canvas_max_y: 1280,
            canvas_step_y: 32,
            canvas_decimals_x: 0,
            canvas_decimals_y: 0,
            canvas_snap: true,
            canvas_dots: true,
            canvas_frame: true,
            action_slider_snap_min: 16,
            action_slider_snap_max: 256,
            action_slider_snap_step: 16,
            scaling_slider_min: 0.1,
            scaling_slider_max: 4.0,
            scaling_slider_step: 0.1,
            megapixels_slider_min: 0.5,
            megapixels_slider_max: 6.0,
            megapixels_slider_step: 0.1,
            snapValue: 64,
            upscaleValue: 1.0,
            targetResolution: 1080,
            targetMegapixels: 2.0,
            rescaleMode: "resolution",
            rescaleValue: 1.0,
            autoDetect: false,
            autoFitOnChange: false,
            selectedCategory: "Standard",
            selectedPreset: null,
            useCustomCalc: false,
            manual_slider_min_w: 16,
            manual_slider_max_w: 2048,
            manual_slider_step_w: 64,
            manual_slider_min_h: 16,
            manual_slider_max_h: 2048,
            manual_slider_step_h: 16,
            // Collapsible sections state
            section_actions_collapsed: false,
            section_scaling_collapsed: false,
            section_autoDetect_collapsed: false,
            section_presets_collapsed: false,
        };

        Object.entries(defaultProperties).forEach(([key, defaultValue]) => {
            this.node.properties[key] = this.node.properties[key] ?? defaultValue;
        });
    }
    
    
    setupNode() {
        const node = this.node;
        const self = this;
        
        // Set minimum size - height will be calculated dynamically
        node.size = [230, 300]; // Initial size, will be adjusted dynamically
        node.min_size = [200, 300]; // Minimum size for basic functionality
        
        // Clear output names for cleaner display
        if (node.outputs) {
            node.outputs.forEach(output => {
                output.name = output.localized_name = "";
            });
        }
        
        // Get widgets
        const widthWidget = node.widgets?.find(w => w.name === 'width');
        const heightWidget = node.widgets?.find(w => w.name === 'height');
        const fpsWidget = node.widgets?.find(w => w.name === 'fps');
		const selectorWidget = node.widgets?.find(w => w.name === 'length_selector');
	    const totFramesWidget = node.widgets?.find(w => w.name === 'total_frames');
		const numSecsWidget = node.widgets?.find(w => w.name === 'num_seconds');
        const rescaleValueWidget = node.widgets?.find(w => w.name === 'rescale_value');
        

        if (rescaleValueWidget) {
            rescaleValueWidget.value = node.properties.rescaleValue;
        }
    
        
        // Initialize values from widgets
        if (widthWidget && heightWidget) {
            node.properties.valueX = widthWidget.value;
            node.properties.valueY = heightWidget.value;
            
            // Initialize intpos based on current values
            node.intpos.x = (widthWidget.value - node.properties.canvas_min_x) / (node.properties.canvas_max_x - node.properties.canvas_min_x);
            node.intpos.y = (heightWidget.value - node.properties.canvas_min_y) / (node.properties.canvas_max_y - node.properties.canvas_min_y);
        }
        
        
        // Store widget references
        this.widthWidget = widthWidget;
        this.heightWidget = heightWidget;
		this.fpsWidget = fpsWidget;
		this.selectorWidget = selectorWidget;
		this.totFramesWidget = totFramesWidget;
		this.numSecsWidget = numSecsWidget;
        		
		
 
        // Override onDrawForeground
        node.onDrawForeground = function(ctx) {
            if (this.flags.collapsed) return;
            self.ensureMinimumSize();
            self.drawInterface(ctx);
        };
        
        // Override mouse handlers
        node.onMouseDown = function(e, pos, canvas) {
            if (e.canvasY - this.pos[1] < 0) return false;
            return self.handleMouseDown(e, pos, canvas);
        };
        
        node.onMouseMove = function(e, pos, canvas) {
            if (!this.capture) {
                self.handleMouseHover(e, pos, canvas);
                return false;
            }
            return self.handleMouseMove(e, pos, canvas);
        };
        
        node.onMouseUp = function(e) {
            if (!this.capture) return false;
            return self.handleMouseUp(e);
        };
        
        node.onPropertyChanged = function(property) {
            self.handlePropertyChange(property);
        };
        
        // Handle resize
        node.onResize = function() {
            self.ensureMinimumSize();
            app.graph.setDirtyCanvas(true);
        };
        
        // Cleanup
        const origOnRemoved = node.onRemoved;
        node.onRemoved = function() {
            if (self.dimensionCheckInterval) {
                clearInterval(self.dimensionCheckInterval);
                self.dimensionCheckInterval = null;
            }
            if (self.tooltipTimer) {
                clearTimeout(self.tooltipTimer);
                self.tooltipTimer = null;
            }
            if (self.customInputDialog) {
                self.closeCustomInputDialog();
            }
            if (origOnRemoved) origOnRemoved.apply(this, arguments);
        };
        
        // Initial configuration
        node.onGraphConfigured = function() {
            this.configured = true;
            this.onPropertyChanged();

            
            // Initialize collapsible sections state from properties after full configuration
            self.collapsedSections = {
                actions: this.properties.section_actions_collapsed,
                scaling: this.properties.section_scaling_collapsed,
               presets: this.properties.section_presets_collapsed
            };
        };

                // Hide all backend widgets
        [widthWidget, heightWidget].forEach(widget => {
            if (widget) {
                widget.hidden = true;
                widget.type = "hidden";
                widget.computeSize = () => [0, -4];
            }
        });
    }
    
    drawInterface(ctx) {
        const node = this.node;
        const props = node.properties;
        const margin = 10;
        const spacing = 8;
        
        let currentY = LiteGraph.NODE_TITLE_HEIGHT + 2 + 150;
        
        if (props.mode === "Manual") {
            // Clear controls at the start to avoid stale references
            this.controls = {};
            

            const canvasHeight = 200;
            this.draw2DCanvas(ctx, margin, currentY, node.size[0] - margin * 2, canvasHeight);
            currentY += canvasHeight + spacing;
            
            this.drawInfoText(ctx, currentY);
            currentY += 15 + spacing;
			

            
            // Draw info message outside of any section background
            if (props.useCustomCalc && props.selectedCategory) {
                const messageHeight = this.drawInfoMessage(ctx, currentY);
                if (messageHeight > 0) {
                    currentY += messageHeight + spacing;
                }
            }
            
            // Draw output values after all sections to ensure controls are preserved
            this.drawOutputValues(ctx);

        }
        
        const neededHeight = currentY + 20;
        // Always adjust height to match content, allowing shrinking when sections are collapsed
        if (node.size[1] !== neededHeight) {
            node.size[1] = Math.max(neededHeight, node.min_size[1]);
        }
        
        // Draw tooltip last so it appears on top
        if (this.showTooltip && this.tooltipElement && this.tooltips[this.tooltipElement]) {
            this.drawTooltip(ctx);
        }
    }

    drawSection(ctx, title, x, y, w, h) {
        ctx.fillStyle = "rgba(0,0,0,0.2)";
        ctx.strokeStyle = "rgba(255,255,255,0.1)";
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.roundRect(x, y, w, h, 6);
        ctx.fill();
        ctx.stroke();

        ctx.fillStyle = "#ccc";
        ctx.font = "bold 12px Arial";
        ctx.textAlign = "center";
        ctx.fillText(title, x + w / 2, y + 10);
    }
    
   
    
    drawOutputValues(ctx) {
		
        const node = this.node;
        const props = node.properties;
        
        ctx.font = "bold 14px Arial";
        ctx.textAlign = "right";
        ctx.textBaseline = "middle";
        
        if (this.widthWidget && this.heightWidget) {
            // Shift values up slightly to better match visual center of slots
            const y_offset_1 = 5 + (LiteGraph.NODE_SLOT_HEIGHT * 0.5);
            const y_offset_2 = 5 + (LiteGraph.NODE_SLOT_HEIGHT * 1.5);
            const y_offset_3 = 5 + (LiteGraph.NODE_SLOT_HEIGHT * 2.5);
			const y_offset_4 = 5 + (LiteGraph.NODE_SLOT_HEIGHT * 3.5);
  
            // Calculate clickable area dimensions
            const valueAreaWidth = 60; // Wider area for better clicking
            const valueAreaHeight = 20;
            const valueAreaX = node.size[0] - valueAreaWidth - 5;

            // Width value area
            this.controls.widthValueArea = {
                x: valueAreaX,
                y: y_offset_1 - valueAreaHeight/2,
                w: valueAreaWidth,
                h: valueAreaHeight
            };
            
            // Draw background for width value area if hovered
            if (this.hoverElement === 'widthValueArea') {
                ctx.fillStyle = "rgba(136, 153, 255, 0.2)";
                ctx.strokeStyle = "rgba(136, 153, 255, 0.5)";
                ctx.lineWidth = 1;
                ctx.beginPath();
                ctx.roundRect(valueAreaX, y_offset_1 - valueAreaHeight/2, valueAreaWidth, valueAreaHeight, 4);
                ctx.fill();
                ctx.stroke();
            }

            ctx.font = "11px Arial";
            ctx.fillStyle = "rgba(200, 200, 200, 0.8)";
            ctx.fillText("video_width", node.size[0] - 20, y_offset_1);
            
            // Height value area
            this.controls.heightValueArea = {
                x: valueAreaX,
                y: y_offset_2 - valueAreaHeight/2,
                w: valueAreaWidth,
                h: valueAreaHeight
            };
            
            // Draw background for height value area if hovered
            if (this.hoverElement === 'heightValueArea') {
                ctx.fillStyle = "rgba(248, 136, 153, 0.2)";
                ctx.strokeStyle = "rgba(248, 136, 153, 0.5)";
                ctx.lineWidth = 1;
                ctx.beginPath();
                ctx.roundRect(valueAreaX, y_offset_2 - valueAreaHeight/2, valueAreaWidth, valueAreaHeight, 4);
                ctx.fill();
                ctx.stroke();
            }
          
		    ctx.fillStyle = "rgba(200, 200, 200, 0.8)";
            ctx.fillText("video_height", node.size[0] - 20, y_offset_2);
            ctx.fillText("total_frames", node.size[0] - 20, y_offset_3);
			ctx.fillText("fps", node.size[0] - 20, y_offset_4);

        }
		else {
			console.log("empty");
		}
    }
    
    drawPrimaryControls(ctx, y) {
        const node = this.node;
        const props = node.properties;
        const margin = 20;
        const buttonWidth = 70;
        const gap = 5;
        let x = margin;

    }
    
    draw2DCanvas(ctx, x, y, w, h) {
        const node = this.node;
        const props = node.properties;
        
        this.controls.canvas2d = { x, y, w, h };
        
        const rangeX = props.canvas_max_x - props.canvas_min_x;
        const rangeY = props.canvas_max_y - props.canvas_min_y;
        const aspectRatio = rangeX / rangeY;
        
        let canvasW = w - 20;
        let canvasH = h - 20;
        
        if (aspectRatio > canvasW / canvasH) {
            canvasH = canvasW / aspectRatio;
        } else {
            canvasW = canvasH * aspectRatio;
        }
        
        const offsetX = x + (w - canvasW) / 2;
        const offsetY = y + (h - canvasH) / 2;
        
        this.controls.canvas2d = { x: offsetX, y: offsetY, w: canvasW, h: canvasH };
        
        ctx.fillStyle = "rgba(20,20,20,0.8)";
        ctx.strokeStyle = "rgba(0,0,0,0.5)";
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.roundRect(offsetX - 4, offsetY - 4, canvasW + 8, canvasH + 8, 6);
        ctx.fill();
        ctx.stroke();
        
        if (props.canvas_dots) {
            ctx.fillStyle = "rgba(200,200,200,0.5)";
            ctx.beginPath();
            let stX = canvasW * props.canvas_step_x / rangeX;
            let stY = canvasH * props.canvas_step_y / rangeY;
            for (let ix = stX; ix < canvasW; ix += stX) {
                for (let iy = stY; iy < canvasH; iy += stY) {
                    ctx.rect(offsetX + ix - 0.5, offsetY + iy - 0.5, 1, 1);
                }
            }
            ctx.fill();
        }
        
        if (props.canvas_frame) {
            ctx.fillStyle = "rgba(150,150,250,0.1)";
            ctx.strokeStyle = "rgba(150,150,250,0.7)";
            ctx.lineWidth = 1.5;
            ctx.beginPath();
            ctx.rect(offsetX, offsetY + canvasH * (1 - node.intpos.y), 
                    canvasW * node.intpos.x, canvasH * node.intpos.y);
            ctx.fill();
            ctx.stroke();
        }
        
        const knobX = offsetX + canvasW * node.intpos.x;
        const knobY = offsetY + canvasH * (1 - node.intpos.y);
        
        ctx.fillStyle = "#FFF";
        ctx.strokeStyle = "#000";
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(knobX, knobY, 8, 0, 2 * Math.PI);
        ctx.fill();
        ctx.stroke();
    }
    
    drawInfoText(ctx, y) {
        const node = this.node;
        if (this.widthWidget && this.heightWidget) {
            const width = this.widthWidget.value;
            const height = this.heightWidget.value;
			const fps = this.fpsWidget.value;
			const secs = this.numSecsWidget.value;
			const nframes = this.totFramesWidget.value;
			const sele = this.selectorWidget.value;
            const mp = ((width * height) / 1000000).toFixed(2);
            const aspectRatio = (width / height).toFixed(2);
            const pResolution = this.getClosestPResolution(width, height);
			const calcSecs = (nframes / fps).toFixed(1);
			const calcFrames = (fps * secs).toFixed(0);
            
			console.log(sele);
            ctx.fillStyle = "#bbb";
            ctx.font = "12px Arial";
            ctx.textAlign = "center";
            ctx.fillText(`${width} × ${height}  `,        node.size[0] / 2, y+15);
			if (sele == "Use # Frames") {
				ctx.fillText(`FRAMES:${nframes}   FPS:${fps}   DUR:${calcSecs}  `,        node.size[0] / 2, y);
			}
			else {
				ctx.fillText(`FRAMES:${calcFrames}   FPS:${fps}   DUR:${secs}  `,        node.size[0] / 2, y);
			}
			
        }
    }
    



    
   
    
   
    
    // Mouse handling methods
    handleMouseDown(e, pos, canvas) {
        const node = this.node;
        const props = node.properties;
        
        const relX = e.canvasX - node.pos[0];
        const relY = e.canvasY - node.pos[1];
        
        if (props.mode === "Manual") {
            const c2d = this.controls.canvas2d;
            if (c2d && this.isPointInControl(relX, relY, c2d)) {
                node.capture = 'canvas2d';
                node.captureInput(true);
                this.updateCanvasValue(relX - c2d.x, relY - c2d.y, c2d.w, c2d.h, e.shiftKey, e.ctrlKey);
                return true;
            }
        }
        
        for (const key in this.controls) {
            if (this.isPointInControl(relX, relY, this.controls[key])) {
                log.debug(`Mouse down on control: ${key} at (${relX}, ${relY})`);
                
                if (key.endsWith('Btn') || key === 'detectedInfo') {
                    this.handleButtonClick(key);
                    return true;
                }
                if (key.endsWith('Slider')) {
                    node.capture = key;
                    node.captureInput(true);
                    this.updateSliderValue(key, relX - this.controls[key].x, this.controls[key].w);
                    return true;
                }
                if (key.endsWith('Dropdown')) {
                    this.showDropdownMenu(key, e);
                    return true;
                }
                if (key.endsWith('Toggle')) {
                    this.handleToggleClick(key);
                    return true;
                }
                if (key.endsWith('Checkbox')) {
                    this.handleCheckboxClick(key);
                    return true;
                }
                if (key.endsWith('Radio')) {
                    this.handleRadioClick(key);
                    return true;
                }
                if (key.endsWith('ValueArea')) {
                    // Open dialog immediately on mousedown
                    log.debug(`Detected ValueArea click: ${key}`);
                    this.showCustomValueDialog(key, e);
                    return true;
                }
                if (key.endsWith('Header')) {
                    this.handleSectionHeaderClick(key);
                    return true;
                }
            }
        }
        
        log.debug(`No control found at (${relX}, ${relY}). Available controls:`, Object.keys(this.controls));
        
        return false;
    }
    
    handleMouseMove(e, pos, canvas) {
        const node = this.node;
        
        if (!node.capture) return false;
        
        // If the mouse button is released, but we are still capturing, handle it as a mouse up event
        if (e.buttons === 0) {
            this.handleMouseUp(e);
            return true;
        }
        
        const relX = e.canvasX - node.pos[0];
        const relY = e.canvasY - node.pos[1];
        
        if (node.capture === 'canvas2d') {
            const c2d = this.controls.canvas2d;
            if (c2d) {
                this.updateCanvasValue(relX - c2d.x, relY - c2d.y, c2d.w, c2d.h, e.shiftKey, e.ctrlKey);
            }
            return true;
        }
        
        if (node.capture.endsWith('Slider')) {
            const control = this.controls[node.capture];
            if (control) {
                this.updateSliderValue(node.capture, relX - control.x, control.w);
            }
            return true;
        }
        
        return false;
    }
    
    handleMouseHover(e, pos, canvas) {
        const node = this.node;
        const relX = e.canvasX - node.pos[0];
        const relY = e.canvasY - node.pos[1];
        
        let newHover = null;
        
        for (const element in this.controls) {
            if (this.isPointInControl(relX, relY, this.controls[element])) {
                newHover = element;
                break;
            }
        }
        
 
    }
    

    handleMouseUp(e) {
        const node = this.node;
        
        if (!node.capture) return false;
        
        node.capture = false;
        node.captureInput(false);
        
        if (this.widthWidget && this.heightWidget) {
            this.widthWidget.value = node.properties.valueX;
            this.heightWidget.value = node.properties.valueY;
        }
        
        this.updateRescaleValue();
        
        return true;
    }
    
    handlePropertyChange(property) {
        const node = this.node;
        if (!node.configured) return;
        
        node.intpos.x = (node.properties.valueX - node.properties.canvas_min_x) / 
                       (node.properties.canvas_max_x - node.properties.canvas_min_x);
        node.intpos.y = (node.properties.valueY - node.properties.canvas_min_y) / 
                       (node.properties.canvas_max_y - node.properties.canvas_min_y);
        
        node.intpos.x = Math.max(0, Math.min(1, node.intpos.x));
        node.intpos.y = Math.max(0, Math.min(1, node.intpos.y));
        
        app.graph.setDirtyCanvas(true);
    }
    
    handleButtonClick(buttonName) {
        const actions = {
            swapBtn: () => this.handleSwap(),
            snapBtn: () => this.handleSnap(),
            megapixelsBtn: () => this.handleMegapixelsScale(),
            detectedInfo: () => this.handleDetectedClick()
        };
        actions[buttonName]?.();
    }

    handleToggleClick(toggleName) {
        const props = this.node.properties;
        if (toggleName === 'autoDetectToggle') {
            props.autoDetect = !props.autoDetect;
            if (props.autoDetect) this.startAutoDetect();
            else this.stopAutoDetect();
            const widget = this.node.widgets?.find(w => w.name === 'auto_detect');
            if (widget) widget.value = props.autoDetect;
            app.graph.setDirtyCanvas(true);
        }
    }

    handleCheckboxClick(checkboxName) {
        const props = this.node.properties;
        if (checkboxName === 'autoFitCheckbox' && props.selectedCategory) {
            props.autoFitOnChange = !props.autoFitOnChange;
        } else if (checkboxName === 'customCalcCheckbox') {
            props.useCustomCalc = !props.useCustomCalc;
        }
        app.graph.setDirtyCanvas(true);
    }

    handleRadioClick(radioName) {
        const props = this.node.properties;
        const radioMap = {
            upscaleRadio: 'manual',
            resolutionRadio: 'resolution',
            megapixelsRadio: 'megapixels'
        };
        props.rescaleMode = radioMap[radioName];
        this.updateRescaleValue();
        app.graph.setDirtyCanvas(true);
    }
    
    handleSectionHeaderClick(headerKey) {
        const sectionKey = headerKey.replace('Header', '');
        this.collapsedSections[sectionKey] = !this.collapsedSections[sectionKey];
        
        // Save state to properties
        const propertyKey = `section_${sectionKey}_collapsed`;
        this.node.properties[propertyKey] = this.collapsedSections[sectionKey];
        
        // Force immediate redraw to recalculate size
        app.graph.setDirtyCanvas(true, true);
        
        log.debug(`Section ${sectionKey} ${this.collapsedSections[sectionKey] ? 'collapsed' : 'expanded'}`);
    }
    
    // Helper methods
    validateWidgets() {
        return this.widthWidget && this.heightWidget;
    }
    
    setDimensions(width, height) {
        if (!this.validateWidgets()) return;
        
        // Update properties
        this.node.properties.valueX = width;
        this.node.properties.valueY = height;
        
        // Then update widgets
        this.widthWidget.value = width;
        this.heightWidget.value = height;
        
        // Update UI
        this.handlePropertyChange();
        this.updateRescaleValue();

        this.updateCanvasFromWidgets();
        
        // Force canvas redraw to update 2D slider position
        app.graph.setDirtyCanvas(true);
    }
    
    updateCanvasFromWidgets() {
        // Aktualizuj pozycję canvas 2D na podstawie wartości widgetów
        if (!this.validateWidgets()) return;
        
        const node = this.node;
        const props = node.properties;
        
        // Aktualizuj properties na podstawie widgetów
        props.valueX = this.widthWidget.value;
        props.valueY = this.heightWidget.value;
        
        // Przelicz pozycję intpos dla canvas 2D
        node.intpos.x = (this.widthWidget.value - props.canvas_min_x) / (props.canvas_max_x - props.canvas_min_x);
        node.intpos.y = (this.heightWidget.value - props.canvas_min_y) / (props.canvas_max_y - props.canvas_min_y);
        
        // Ogranicz do zakresu 0-1
        node.intpos.x = Math.max(0, Math.min(1, node.intpos.x));
        node.intpos.y = Math.max(0, Math.min(1, node.intpos.y));
        
        // Aktualizuj rescale value
        this.updateRescaleValue();
        
        // Wymuś przerysowanie canvas
        app.graph.setDirtyCanvas(true);
    }
    
    setCanvasTextStyle(ctx, style = {}) {
        const defaults = {
            fillStyle: "#ccc",
            font: "12px Arial",
            textAlign: "center",
            textBaseline: "middle"
        };
        const finalStyle = { ...defaults, ...style };
        
        Object.entries(finalStyle).forEach(([key, value]) => {
            ctx[key] = value;
        });
    }
    
  

    // Value update methods
    updateCanvasValue(x, y, w, h, shiftKey, ctrlKey) {
        const node = this.node;
        const props = node.properties;
        
        let vX = Math.max(0, Math.min(1, x / w));
        let vY = Math.max(0, Math.min(1, 1 - y / h));
        
        // Ctrl+Shift: zmiana rozmiaru po 1px z zachowaniem proporcji
        if (ctrlKey && shiftKey) {
            // Zachowaj obecne proporcje
            const currentAspect = this.widthWidget.value / this.heightWidget.value;
            
            let newX = props.canvas_min_x + (props.canvas_max_x - props.canvas_min_x) * vX;
            let newY = props.canvas_min_y + (props.canvas_max_y - props.canvas_min_y) * vY;
            
            // Zaokrąglij do 1px
            newX = Math.round(newX);
            newY = Math.round(newY);
            
            // Zachowaj proporcje - dostosuj Y na podstawie X
            newY = Math.round(newX / currentAspect);
            
            // Przelicz z powrotem na pozycje vX, vY
            vX = (newX - props.canvas_min_x) / (props.canvas_max_x - props.canvas_min_x);
            vY = (newY - props.canvas_min_y) / (props.canvas_max_y - props.canvas_min_y);
        }
        // Shift: przeciąganie z zachowaniem proporcji
        else if (shiftKey && !ctrlKey) {
            // Zachowaj obecne proporcje
            const currentAspect = this.widthWidget.value / this.heightWidget.value;
            
            let newX = props.canvas_min_x + (props.canvas_max_x - props.canvas_min_x) * vX;
            let newY = props.canvas_min_y + (props.canvas_max_y - props.canvas_min_y) * vY;
            
            // Zastosuj snap
            let sX = props.canvas_step_x / (props.canvas_max_x - props.canvas_min_x);
            let sY = props.canvas_step_y / (props.canvas_max_y - props.canvas_min_y);
            vX = Math.round(vX / sX) * sX;
            
            // Przelicz newX po snap
            newX = props.canvas_min_x + (props.canvas_max_x - props.canvas_min_x) * vX;
            
            // Zachowaj proporcje - dostosuj Y na podstawie X
            newY = newX / currentAspect;
            
            // Przelicz z powrotem na pozycję vY
            vY = (newY - props.canvas_min_y) / (props.canvas_max_y - props.canvas_min_y);
        }
        // Ctrl: zmiana rozmiaru bez snap (poprzednia funkcjonalność Shift)
        else if (ctrlKey && !shiftKey) {
            // Nie stosuj snap - pozostaw vX i vY bez zmian
        }
        // Domyślnie: zastosuj snap
        else {
            let sX = props.canvas_step_x / (props.canvas_max_x - props.canvas_min_x);
            let sY = props.canvas_step_y / (props.canvas_max_y - props.canvas_min_y);
            vX = Math.round(vX / sX) * sX;
            vY = Math.round(vY / sY) * sY;
        }
        
        node.intpos.x = vX;
        node.intpos.y = vY;
        
        let newX = props.canvas_min_x + (props.canvas_max_x - props.canvas_min_x) * vX;
        let newY = props.canvas_min_y + (props.canvas_max_y - props.canvas_min_y) * vY;
        
        const rnX = Math.pow(10, props.canvas_decimals_x);
        const rnY = Math.pow(10, props.canvas_decimals_y);
        newX = Math.round(rnX * newX) / rnX;
        newY = Math.round(rnY * newY) / rnY;
        
        this.setDimensions(newX, newY);
        app.graph.setDirtyCanvas(true);
    }
    
    updateSliderValue(sliderName, x, w) {
        const props = this.node.properties;
        let value = Math.max(0, Math.min(1, x / w));
        
        const sliderConfig = {
            snapSlider: { prop: 'snapValue', min: props.action_slider_snap_min, max: props.action_slider_snap_max, step: props.action_slider_snap_step },
            scaleSlider: { prop: 'upscaleValue', min: props.scaling_slider_min, max: props.scaling_slider_max, step: props.scaling_slider_step, updateOn: 'manual' },
            megapixelsSlider: { prop: 'targetMegapixels', min: props.megapixels_slider_min, max: props.megapixels_slider_max, step: props.megapixels_slider_step, updateOn: 'megapixels' },
            widthSlider: { prop: 'valueX', min: props.manual_slider_min_w, max: props.manual_slider_max_w, step: props.manual_slider_step_w },
            heightSlider: { prop: 'valueY', min: props.manual_slider_min_h, max: props.manual_slider_max_h, step: props.manual_slider_step_h }
        };

        const config = sliderConfig[sliderName];
        if (config) {
            let newValue = config.min + value * (config.max - config.min);
            props[config.prop] = Math.round(newValue / config.step) * config.step;
            
            if (sliderName === 'scaleSlider' || sliderName === 'megapixelsSlider') {
                 props[config.prop] = parseFloat(props[config.prop].toFixed(1));
            }

            if (config.updateOn && props.rescaleMode === config.updateOn) {
                this.updateRescaleValue();
            }

            if (sliderName === 'widthSlider') {
                this.setDimensions(props.valueX, this.heightWidget.value);
            } else if (sliderName === 'heightSlider') {
                this.setDimensions(this.widthWidget.value, props.valueY);
            } else if (sliderName.includes('Slider')) {
                this.handlePropertyChange();
            }
        }
        
        app.graph.setDirtyCanvas(true);
    }
    
    showDropdownMenu(dropdownName, e) {
        const props = this.node.properties;
        let items, callback;
        
        if (dropdownName === 'categoryDropdown') {
            items = Object.keys(this.presetCategories);
            callback = (value) => {
                props.selectedCategory = value;
                props.selectedPreset = null;
                app.graph.setDirtyCanvas(true);
            };
        } else if (dropdownName === 'presetDropdown' && props.selectedCategory) {
            const presets = this.presetCategories[props.selectedCategory];
            items = Object.keys(presets).map(name => `${name} (${presets[name].width}×${presets[name].height})`);
            callback = (value) => {
               // Handle preset names that may contain parentheses by removing the last part with dimensions
               const lastParenIndex = value.lastIndexOf(' (');
               const presetName = value.substring(0, lastParenIndex);
               this.applyPreset(props.selectedCategory, presetName);
            };
        } 
        
        if (items?.length) {
            new LiteGraph.ContextMenu(items, { event: e.originalEvent || e, callback });
        }
    }
    
    showCustomValueDialog(valueAreaKey, e) {
        if (this.inputDialogActive) return;
        
        log.debug(`Clicked on value area: ${valueAreaKey}`);
        
        // Determine the type and current value based on the control key
        let valueType, currentValue, propertyName, minValue = 0.01;
        
        if (valueAreaKey === 'scaleValueArea') {
            valueType = 'Scale Factor';
            currentValue = this.node.properties.upscaleValue;
            propertyName = 'upscaleValue';
        
        } else if (valueAreaKey === 'megapixelsValueArea') {
            valueType = 'Megapixels';
            currentValue = this.node.properties.targetMegapixels;
            propertyName = 'targetMegapixels';
        } else if (valueAreaKey === 'snapValueArea') {
            valueType = 'Snap Value';
            currentValue = this.node.properties.snapValue;
            propertyName = 'snapValue';
            minValue = 1;
        } else if (valueAreaKey === 'widthValueArea') {
            valueType = 'Width';
            currentValue = this.widthWidget ? this.widthWidget.value : this.node.properties.valueX;
            propertyName = 'width';
            minValue = 64;
        } else if (valueAreaKey === 'heightValueArea') {
            valueType = 'Height';
            currentValue = this.heightWidget ? this.heightWidget.value : this.node.properties.valueY;
            propertyName = 'height';
            minValue = 64;
        } else {
            log.debug(`Unknown value area key: ${valueAreaKey}`);
            return;
        }
        
        log.debug(`Opening dialog for ${valueType} with current value: ${currentValue}`);
        this.createCustomInputDialog(valueType, currentValue, propertyName, minValue, e);
    }
    
    createCustomInputDialog(valueType, currentValue, propertyName, minValue, e) {
        this.inputDialogActive = true;
        log.debug(`Creating dialog for ${valueType}, current: ${currentValue}`);
        
        // Create overlay
        const overlay = document.createElement('div');
        this.customInputOverlay = overlay;
        overlay.style.cssText = `
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,0.5); z-index: 9999;
        `;
        overlay.addEventListener('mousedown', () => this.closeCustomInputDialog());
        document.body.appendChild(overlay);

        // Create dialog container
        const dialog = document.createElement('div');
        this.customInputDialog = dialog;
        dialog.className = 'litegraph-custom-input-dialog';
        dialog.addEventListener('mousedown', (e) => e.stopPropagation()); // Prevent clicks inside from closing
        dialog.style.cssText = `
            position: fixed;
            background: linear-gradient(135deg, #2a2a2a 0%, #1e1e1e 100%);
            border: 2px solid #555; border-radius: 8px; padding: 20px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.8); z-index: 10000;
            font-family: Arial, sans-serif; min-width: 280px;
        `;
        
        // Position dialog
        const x = e.clientX ? e.clientX + 20 : (window.innerWidth - 280) / 2;
        const y = e.clientY ? e.clientY + 20 : (window.innerHeight - 200) / 2;
        dialog.style.left = `${Math.max(10, Math.min(x, window.innerWidth - 300))}px`;
        dialog.style.top = `${Math.max(10, Math.min(y, window.innerHeight - 200))}px`;
        
        // Create dialog content
        dialog.innerHTML = `
            <div style="color: #fff; font-size: 16px; font-weight: bold; margin-bottom: 15px; text-align: center;">Set Custom ${valueType}</div>
            <div style="margin-bottom: 10px;">
                <label style="color: #ccc; font-size: 12px; display: block; margin-bottom: 5px;">Current: ${this.formatValueForDisplay(currentValue, valueType)}</label>
                <input type="${valueType === 'Scale Factor' ? 'text' : 'number'}" id="customValueInput" value="${currentValue}" step="0.01" min="${minValue}"
                       style="width: 100%; padding: 8px; border: 1px solid #555; border-radius: 4px; background: #333; color: #fff; font-size: 14px; box-sizing: border-box;">
            </div>
            <div id="validationMessage" style="color: #f55; font-size: 11px; margin-bottom: 5px; min-height: 15px;"></div>
            <div id="infoMessage" style="color: #999; font-size: 11px; margin-bottom: 10px; min-height: 15px; text-align: center;"></div>
            <div style="display: flex; gap: 10px; justify-content: flex-end;">
                <button id="cancelBtn" style="padding: 8px 16px; border: 1px solid #555; border-radius: 4px; background: #444; color: #ccc; cursor: pointer; font-size: 12px;">Cancel</button>
                <button id="applyBtn" style="padding: 8px 16px; border: 1px solid #5af; border-radius: 4px; background: #5af; color: #fff; cursor: pointer; font-size: 12px;">Apply</button>
            </div>
        `;
        
        document.body.appendChild(dialog);
        
        // Get elements
        const input = dialog.querySelector('#customValueInput');
        const validationMsg = dialog.querySelector('#validationMessage');
        const infoMsg = dialog.querySelector('#infoMessage');
        const cancelBtn = dialog.querySelector('#cancelBtn');
        const applyBtn = dialog.querySelector('#applyBtn');
        
        if (valueType === 'Scale Factor') {
            infoMsg.textContent = 'Tip: Use /2 for 0.5x, /4 for 0.25x, etc.';
        }
        
        // Focus and select input
        setTimeout(() => { input.focus(); input.select(); }, 50);
        
        // Real-time validation
        const validateInput = () => {
            const value = this.parseCustomInputValue(input.value, valueType);
            if (isNaN(value) || value < minValue) {
                let errorMsg = `Value must be ≥ ${minValue}`;
                if (typeof input.value === 'string' && input.value.startsWith('/')) {
                    const divisor = parseFloat(input.value.substring(1));
                    if (isNaN(divisor) || divisor === 0) errorMsg = 'Invalid divisor after /';
                }
                validationMsg.textContent = errorMsg;
                applyBtn.disabled = true; applyBtn.style.opacity = '0.5';
                return false;
            } else {
                validationMsg.textContent = '';
                applyBtn.disabled = false; applyBtn.style.opacity = '1';
                return true;
            }
        };
        
        // Event listeners
        input.addEventListener('input', validateInput);
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && validateInput()) this.applyCustomValue(propertyName, this.parseCustomInputValue(input.value, valueType), valueType);
            else if (e.key === 'Escape') this.closeCustomInputDialog();
        });
        cancelBtn.addEventListener('click', () => this.closeCustomInputDialog());
        applyBtn.addEventListener('click', () => {
            if (validateInput()) this.applyCustomValue(propertyName, this.parseCustomInputValue(input.value, valueType), valueType);
        });
        
        validateInput();
    }
    
    formatValueForDisplay(value, valueType) {
        if (valueType === 'Scale Factor') {
            return value.toFixed(1) + 'x';
        } else if (valueType === 'Resolution Scale') {
            return '×' + value.toFixed(2);
        } else if (valueType === 'Megapixels') {
            return value.toFixed(1) + 'MP';
        } else if (valueType === 'Width' || valueType === 'Height') {
            return value.toString() + 'px';
        } else {
            return value.toString();
        }
    }
    
    applyCustomValue(propertyName, value, valueType) {
        const props = this.node.properties;
        
        if (propertyName === 'upscaleValue') {
            props.upscaleValue = value;
            if (props.rescaleMode === 'manual') {
                this.updateRescaleValue();
            }
        } else if (propertyName === 'targetResolution') {
            // For resolution, we need to reverse-calculate the target resolution from the scale factor
            if (this.validateWidgets()) {
                const currentPixels = this.widthWidget.value * this.heightWidget.value;
                const targetPixels = currentPixels * (value * value);
                const targetP = Math.sqrt(targetPixels / (16/9));
                props.targetResolution = Math.round(targetP);
                if (props.rescaleMode === 'resolution') {
                    this.updateRescaleValue();
                }
            }
        } else if (propertyName === 'targetMegapixels') {
            props.targetMegapixels = value;
            if (props.rescaleMode === 'megapixels') {
                this.updateRescaleValue();
            }
        } else if (propertyName === 'snapValue') {
            props.snapValue = Math.round(value);
        } else if (propertyName === 'width') {
            const newWidth = Math.round(value);
            const currentHeight = this.heightWidget ? this.heightWidget.value : props.valueY;
            this.setDimensions(newWidth, currentHeight);
        } else if (propertyName === 'height') {
            const newHeight = Math.round(value);
            const currentWidth = this.widthWidget ? this.widthWidget.value : props.valueX;
            this.setDimensions(currentWidth, newHeight);
        }
        
        this.closeCustomInputDialog();
        app.graph.setDirtyCanvas(true);
        
        log.debug(`Applied custom ${valueType}: ${value}`);
    }
    
    closeCustomInputDialog() {
        if (this.customInputDialog) {
            document.body.removeChild(this.customInputDialog);
            this.customInputDialog = null;
        }
        if (this.customInputOverlay) {
            document.body.removeChild(this.customInputOverlay);
            this.customInputOverlay = null;
        }
        this.inputDialogActive = false;
    }

    parseCustomInputValue(rawValue, valueType) {
        if (valueType === 'Scale Factor' && typeof rawValue === 'string' && rawValue.startsWith('/')) {
            const divisor = parseFloat(rawValue.substring(1));
            if (!isNaN(divisor) && divisor !== 0) {
                return 1 / divisor;
            }
        }
        return parseFloat(rawValue);
    }
    
    // Action handlers
    handleSwap() {
        if (!this.validateWidgets()) return;
        
        const newWidth = this.heightWidget.value;
        const newHeight = this.widthWidget.value;
        this.setDimensions(newWidth, newHeight);
    }
    
    handleSnap() {
        if (!this.validateWidgets()) return;
        
        const snap = this.node.properties.snapValue;
        const newWidth = Math.round(this.widthWidget.value / snap) * snap;
        const newHeight = Math.round(this.heightWidget.value / snap) * snap;
        this.setDimensions(newWidth, newHeight);
    }
    
   
    handleMegapixelsScale() {
        this.applyScaling(() => this.calculateMegapixelsScale(this.node.properties.targetMegapixels));
    }
    
  
   
    
  
    handleDetectedClick() {
        // Funkcja obsługująca kliknięcie na napis "Detected" - nakłada oryginalne wymiary wykrytego zdjęcia
        if (!this.detectedDimensions) {
            log.debug("Detected click: No detected dimensions available");
            return;
        }
        
        if (!this.widthWidget || !this.heightWidget) {
            log.debug("Detected click: Width or height widget not found");
            return;
        }
        
        // Ustaw oryginalne wymiary wykrytego zdjęcia
        this.setDimensions(this.detectedDimensions.width, this.detectedDimensions.height);
        
        log.debug(`Detected click applied: Set dimensions to ${this.detectedDimensions.width}x${this.detectedDimensions.height}`);
    }
    
    applyDimensionChange() {
        const props = this.node.properties;
        let { value: width } = this.widthWidget;
        let { value: height } = this.heightWidget;

        if (props.useCustomCalc && props.selectedCategory) {
            ({ width, height } = this.applyCustomCalculation(width, height, props.selectedCategory));
        }

        const newWidth = Math.max(props.canvas_min_x, Math.min(props.canvas_max_x, width));
        const newHeight = Math.max(props.canvas_min_y, Math.min(props.canvas_max_y, height));
        
        this.setDimensions(newWidth, newHeight);
    }

 


    getClosestPResolution(width, height) {
        const pValue = Math.sqrt(width * height * 9 / 16);
        return `(${Math.round(pValue)}p)`;
    }
    

    calculateMegapixelsScale(targetMP) {
        const targetPixels = targetMP * 1000000;
        return this.calculateScaleFromPixels(targetPixels);
    }
    
    calculateScaleFromPixels(targetPixels) {
        if (!this.widthWidget || !this.heightWidget) return 1.0;
        const currentPixels = this.widthWidget.value * this.heightWidget.value;
        return Math.sqrt(targetPixels / currentPixels);
    }
    

    
  
    

    
    isPointInControl(x, y, control) {
        if (!control) return false;
        return x >= control.x && x <= control.x + control.w &&
               y >= control.y && y <= control.y + control.h;
    }
}

// Register the extension
app.registerExtension({
    name: "extTKVideoUserInputs",
    async beforeRegisterNodeDef(nodeType, nodeData, _app) {
		
        if (nodeData.name === "TKVideoUserInputs") {
		
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function() {
                onNodeCreated?.apply(this, []);
                this.tkvideouserinputs = new TKVideoUserInputsCanvas(this);
            };
        }
    }
});
