globalThis.browserControlMaskCapture = async (dataUrl, privacy) => {
    const binaryInput = atob(dataUrl.split(",")[1]);
    const bytesInput = Uint8Array.from(binaryInput, (char) => char.charCodeAt(0));
    const bitmap = await createImageBitmap(new Blob([bytesInput], { type: "image/png" }));
    try {
        const canvas = new OffscreenCanvas(bitmap.width, bitmap.height);
        const context = canvas.getContext("2d");
        if (!context || !privacy.width || !privacy.height)
            throw new Error("Screenshot masking unavailable; capture withheld.");
        context.drawImage(bitmap, 0, 0);
        context.fillStyle = "#171717";
        const scaleX = bitmap.width / privacy.width;
        const scaleY = bitmap.height / privacy.height;
        for (const rect of privacy.rectangles) {
            // Extra padding avoids fractional-pixel edges leaking glyphs.
            context.fillRect(
                Math.floor(rect.x * scaleX) - 3,
                Math.floor(rect.y * scaleY) - 3,
                Math.ceil(rect.width * scaleX) + 6,
                Math.ceil(rect.height * scaleY) + 6,
            );
        }
        const bytes = new Uint8Array(await (await canvas.convertToBlob({ type: "image/png" })).arrayBuffer());
        let binary = "";
        for (let at = 0; at < bytes.length; at += 32768)
            binary += String.fromCharCode(...bytes.subarray(at, at + 32768));
        return `data:image/png;base64,${btoa(binary)}`;
    } finally {
        bitmap.close();
    }
};
