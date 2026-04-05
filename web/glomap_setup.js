import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "GLOMAP.SetupNodeDynamic",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "GLOMAPSetup") {
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                const r = onNodeCreated ? onNodeCreated.apply(this, arguments) : undefined;
                
                const use_portable = this.widgets.find(w => w.name === "use_blender_portable");
                const blender_path = this.widgets.find(w => w.name === "blender_path");
                
                if (use_portable && blender_path) {
                    const updateUI = () => {
                        if (use_portable.value) {
                            blender_path.value = "ComfyUI/custom_nodes/ComfyUI-GLOMAP/bin/blender";
                            // Optionally dim it out or show it's auto-managed
                        } else {
                            if (blender_path.value.includes("ComfyUI-GLOMAP") || blender_path.value === "") {
                                blender_path.value = "proporciona un path";
                            }
                        }
                    };
                    
                    const origCallback = use_portable.callback;
                    use_portable.callback = function() {
                        if (origCallback) origCallback.apply(this, arguments);
                        updateUI();
                    };
                    
                    setTimeout(updateUI, 100);
                }
                
                return r;
            };
        }
    }
});
