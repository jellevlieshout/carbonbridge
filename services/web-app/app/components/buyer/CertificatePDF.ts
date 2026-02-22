import { jsPDF } from "jspdf";

interface CertificateData {
    orderId: string;
    projectName: string;
    projectCountry?: string | null;
    registryName?: string | null;
    vintageYear?: number | null;
    methodology?: string | null;
    quantity: number;
    totalEur: number;
    serialNumber: string;
    retirementDate: string;
    retirementReference?: string | null;
}

const CANOPY = "#1B3A2D";
const CANOPY_LIGHT = "#2D5A47";
const SLATE = "#334155";
const MUTED = "#94A3B8";
const LINEN = "#F4F1EA";

async function loadLogoAsDataUrl(): Promise<string | null> {
    try {
        const res = await fetch("/favicon.png");
        const blob = await res.blob();
        return new Promise((resolve) => {
            const reader = new FileReader();
            reader.onloadend = () => resolve(reader.result as string);
            reader.onerror = () => resolve(null);
            reader.readAsDataURL(blob);
        });
    } catch {
        return null;
    }
}

export async function generateCertificatePDF(data: CertificateData): Promise<void> {
    const doc = new jsPDF({ orientation: "portrait", unit: "mm", format: "a4" });
    const pw = doc.internal.pageSize.getWidth();
    const ph = doc.internal.pageSize.getHeight();
    const mx = 25; // margin x

    // --- Background ---
    doc.setFillColor(LINEN);
    doc.rect(0, 0, pw, ph, "F");

    // --- Header banner ---
    doc.setFillColor(CANOPY);
    doc.rect(0, 0, pw, 52, "F");

    // Logo
    const logoUrl = await loadLogoAsDataUrl();
    if (logoUrl) {
        doc.addImage(logoUrl, "PNG", mx, 10, 16, 16);
    }

    // Brand name
    doc.setFont("helvetica", "bold");
    doc.setFontSize(18);
    doc.setTextColor("#FFFFFF");
    doc.text("CarbonBridge", logoUrl ? mx + 20 : mx, 22);

    // Subtitle
    doc.setFont("helvetica", "normal");
    doc.setFontSize(9);
    doc.setTextColor("#FFFFFF80");
    doc.text("Voluntary Carbon Credit Marketplace", logoUrl ? mx + 20 : mx, 28);

    // Certificate title
    doc.setFont("helvetica", "bold");
    doc.setFontSize(13);
    doc.setTextColor("#FFFFFF");
    doc.text("CERTIFICATE OF CARBON CREDIT RETIREMENT", pw / 2, 44, { align: "center" });

    // --- DEMO watermark ---
    doc.setFont("helvetica", "bold");
    doc.setFontSize(60);
    doc.setTextColor(200, 200, 200);
    doc.setGState(new doc.GState({ opacity: 0.08 }));
    doc.text("DEMO", pw / 2, ph / 2, { align: "center", angle: 35 });
    doc.setGState(new doc.GState({ opacity: 1 }));

    // --- Decorative line ---
    let y = 62;
    doc.setDrawColor(CANOPY);
    doc.setLineWidth(0.5);
    doc.line(mx, y, pw - mx, y);

    // --- Certifies that ---
    y += 12;
    doc.setFont("helvetica", "normal");
    doc.setFontSize(10);
    doc.setTextColor(MUTED);
    doc.text("This certifies that", pw / 2, y, { align: "center" });

    y += 10;
    doc.setFont("helvetica", "bold");
    doc.setFontSize(16);
    doc.setTextColor(SLATE);
    doc.text("The Bearer of This Certificate", pw / 2, y, { align: "center" });

    y += 8;
    doc.setFont("helvetica", "normal");
    doc.setFontSize(10);
    doc.setTextColor(MUTED);
    doc.text("has permanently retired the following verified carbon credits", pw / 2, y, { align: "center" });

    // --- Divider ---
    y += 10;
    doc.setDrawColor("#CBD5E1");
    doc.setLineWidth(0.3);
    doc.line(mx + 30, y, pw - mx - 30, y);

    // --- Details section ---
    y += 14;

    const drawField = (label: string, value: string, x: number, yPos: number, width?: number): number => {
        doc.setFont("helvetica", "normal");
        doc.setFontSize(8);
        doc.setTextColor(MUTED);
        doc.text(label.toUpperCase(), x, yPos);

        doc.setFont("helvetica", "bold");
        doc.setFontSize(11);
        doc.setTextColor(SLATE);
        const lines = doc.splitTextToSize(value, width || (pw - mx * 2));
        doc.text(lines, x, yPos + 5);
        return yPos + 5 + lines.length * 5;
    };

    // Project name + country
    const projectLabel = data.projectCountry
        ? `${data.projectName} (${data.projectCountry})`
        : data.projectName;
    y = drawField("Project", projectLabel, mx, y);

    // Registry + methodology row
    y += 6;
    const colW = (pw - mx * 2 - 10) / 2;
    drawField("Registry", data.registryName || "Verra VCS", mx, y, colW);
    if (data.methodology) {
        drawField("Methodology", data.methodology, mx + colW + 10, y, colW);
    } else if (data.vintageYear) {
        drawField("Vintage Year", String(data.vintageYear), mx + colW + 10, y, colW);
    }

    // Quantity + value row
    y += 16;
    drawField("Quantity Retired", `${data.quantity} tCO2e`, mx, y, colW);
    drawField("Total Value", `EUR ${data.totalEur.toFixed(2)}`, mx + colW + 10, y, colW);

    // Date + retirement ref row
    y += 16;
    drawField("Retirement Date", data.retirementDate, mx, y, colW);
    if (data.retirementReference) {
        drawField("Retirement Reference", data.retirementReference, mx + colW + 10, y, colW);
    }

    // Serial number
    y += 16;
    doc.setFont("helvetica", "normal");
    doc.setFontSize(8);
    doc.setTextColor(MUTED);
    doc.text("SERIAL NUMBER", mx, y);
    doc.setFont("courier", "normal");
    doc.setFontSize(9);
    doc.setTextColor(SLATE);
    const serialLines = doc.splitTextToSize(data.serialNumber, pw - mx * 2);
    doc.text(serialLines, mx, y + 5);
    y += 5 + serialLines.length * 4;

    // Order reference
    y += 6;
    drawField("Order Reference", data.orderId, mx, y);

    // --- Verification box ---
    y += 20;
    doc.setFillColor("#F0FDF4");
    doc.setDrawColor("#BBF7D0");
    doc.setLineWidth(0.3);
    const boxH = 22;
    doc.roundedRect(mx, y, pw - mx * 2, boxH, 3, 3, "FD");

    doc.setFont("helvetica", "bold");
    doc.setFontSize(9);
    doc.setTextColor(CANOPY);
    doc.text("Registry Verified", mx + 8, y + 9);

    doc.setFont("helvetica", "normal");
    doc.setFontSize(8);
    doc.setTextColor(CANOPY_LIGHT);
    const registryText = `These carbon credits have been verified and permanently retired on the ${data.registryName || "Verra VCS"} Registry.`;
    doc.text(registryText, mx + 8, y + 15);

    // --- Footer ---
    const footerY = ph - 35;
    doc.setDrawColor("#CBD5E1");
    doc.setLineWidth(0.2);
    doc.line(mx, footerY, pw - mx, footerY);

    doc.setFont("helvetica", "normal");
    doc.setFontSize(7);
    doc.setTextColor(MUTED);
    doc.text(
        "This certificate was issued by CarbonBridge and confirms the permanent retirement of the specified carbon credits.",
        pw / 2, footerY + 6, { align: "center" }
    );
    doc.text(
        "Retired credits cannot be re-sold, transferred, or used for any other purpose.",
        pw / 2, footerY + 11, { align: "center" }
    );
    doc.text(
        `Document generated on ${new Date().toLocaleDateString("en-GB", { day: "2-digit", month: "long", year: "numeric" })}`,
        pw / 2, footerY + 16, { align: "center" }
    );
    doc.setFontSize(6);
    doc.text(
        "DEMO CERTIFICATE — For demonstration purposes only. Not a legally binding document.",
        pw / 2, footerY + 22, { align: "center" }
    );

    // --- Download ---
    doc.save(`CarbonBridge-Certificate-${data.orderId.substring(0, 8)}.pdf`);
}
