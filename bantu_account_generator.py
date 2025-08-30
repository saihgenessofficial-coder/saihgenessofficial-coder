#!/usr/bin/env python3
import os, json, hashlib, argparse, datetime
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPM

def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def ensure_dirs(*dirs):
    for d in dirs:
        Path(d).mkdir(parents=True, exist_ok=True)

def make_qr_png(text: str, png_path: str, size_px: int = 512):
    widget = qr.QrCodeWidget(text)
    x0, y0, x1, y1 = widget.getBounds()
    w, h = (x1 - x0), (y1 - y0)
    scale = float(size_px) / max(w, h)
    # Apply scaling via Drawing transform
    d = Drawing(size_px, size_px, transform=[scale, 0, 0, scale, 0, 0])
    d.add(widget)
    renderPM.drawToFile(d, png_path, fmt="PNG")

def save_json(model: dict, json_path: str):
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(model, f, ensure_ascii=False, indent=2)

def make_pdf(model: dict, pdf_path: str, qr_png_path: str, signature_img: str = None):
    width, height = A4
    c = canvas.Canvas(pdf_path, pagesize=A4)
    left = 20*mm; right = width - 20*mm; top = height - 20*mm; bottom = 20*mm

    c.setFillColorRGB(0.05, 0.09, 0.16)
    c.rect(0, height - 40*mm, width, 40*mm, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(width/2, height - 20*mm, "BANTU — Registro de Conta")
    c.setFont("Helvetica", 10)
    c.drawCentredString(width/2, height - 29*mm, "Banco da Nova Terra Universal • Documento Selado")
    c.drawCentredString(width/2, height - 34*mm, datetime.datetime.utcnow().strftime("Gerado em %Y-%m-%d %H:%M UTC"))

    c.setFillColor(colors.black)
    y = height - 50*mm
    line = 6*mm
    def kv(k, v):
        nonlocal y
        c.setFont("Helvetica-Bold", 11); c.drawString(left, y, f"{k}:")
        c.setFont("Helvetica", 11); c.drawString(left + 45*mm, y, v); y -= line

    kv("ID da Conta", model.get("id_conta",""))
    kv("Nome", model.get("nome",""))
    kv("Tipo", model.get("tipo_conta",""))
    kv("Endereço EVM", model.get("endereco_evm",""))
    kv("SHA-256 (endereço)", model.get("hash_sha256",""))
    kv("Status", model.get("status",""))
    kv("Data de Registro", model.get("data_registro",""))

    if os.path.exists(qr_png_path):
        c.setFont("Helvetica-Bold", 11)
        c.drawString(left, y-2*mm, "QR Code (endereço EVM):")
        c.drawImage(qr_png_path, left, y-45*mm, width=40*mm, height=40*mm, preserveAspectRatio=True, mask='auto')
    y -= 50*mm

    c.setFont("Helvetica-Bold", 11); c.drawString(left, y, "Observações:"); y -= line
    c.setFont("Helvetica", 10)
    obs = model.get("observacoes","—")
    for line_txt in obs.splitlines():
        c.drawString(left, y, line_txt[:110]); y -= 5*mm

    y = max(y, 50*mm)
    c.setFont("Helvetica-Bold", 11); c.drawString(left, y+25*mm, "Assinatura:")
    sig_w = 70*mm; sig_h = 20*mm
    if signature_img and os.path.exists(signature_img):
        c.drawImage(signature_img, left, y, width=sig_w, height=sig_h, preserveAspectRatio=True, mask='auto')
        c.setFont("Helvetica", 9); c.setFillColor(colors.HexColor("#555555"))
        c.drawString(left, y-5*mm, f"Assinatura inserida: {os.path.basename(signature_img)}")
    else:
        c.setFillColor(colors.HexColor("#ffffff"))
        c.rect(left, y, sig_w, sig_h, stroke=1, fill=0)
        c.setFont("Helvetica", 9); c.setFillColor(colors.HexColor("#555555"))
        c.drawString(left+2*mm, y + sig_h/2 - 3*mm, "Assinatura pendente (insira imagem para selar).")

    c.setFont("Helvetica-Oblique", 9); c.setFillColor(colors.HexColor("#666666"))
    c.drawCentredString(width/2, 10*mm, "Obra SAIH GENESS — BANTU • Registro de Conta • Para a Glória do Altíssimo")
    c.showPage(); c.save()

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", required=True)
    ap.add_argument("--nome", required=True)
    ap.add_argument("--tipo", required=True, choices=["cliente","ministerio","levita","governo","investidor"])
    ap.add_argument("--address", required=True)
    ap.add_argument("--status", default="publico", choices=["publico","privado"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--sig", default="")
    args = ap.parse_args()

    sha = sha256_hex(args.address)
    now_iso = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    json_dir = os.path.join(args.out, "json")
    pdf_dir = os.path.join(args.out, "pdf")
    qr_dir = os.path.join(args.out, "qrcodes")
    ensure_dirs(json_dir, pdf_dir, qr_dir)

    safe = args.nome.lower().strip().replace(" ", "-")
    json_path = os.path.join(json_dir, f"{safe}.json")
    pdf_path  = os.path.join(pdf_dir,  f"{safe}.pdf")
    qr_path   = os.path.join(qr_dir,   f"{safe}.png")

    make_qr_png(args.address, qr_path, 512)

    model = {
        "id_conta": args.id,
        "nome": args.nome,
        "tipo_conta": args.tipo,
        "endereco_evm": args.address,
        "hash_sha256": sha,
        "qrcode": qr_path,
        "status": args.status,
        "data_registro": now_iso,
        "observacoes": "Conta oficial selada dentro do Banco da Nova Terra (BANTU) — Obra SAIH GENESS.",
        "assinatura_responsavel": "Kizequiel Guilherme Nzau – Servo do Senhor, Responsável terreno da Obra",
        "documentos": { "pdf_selado": pdf_path, "json_original": json_path }
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(model, f, ensure_ascii=False, indent=2)

    make_pdf(model, pdf_path, qr_path, signature_img=args.sig if args.sig else None)

    print("✅ JSON:", json_path)
    print("✅ PDF :", pdf_path)
    print("✅ QR  :", qr_path)
    print("\nS3 upload:")
    print(f"aws s3 cp \"{json_path}\" s3://bantu-banco-da-nova-terra/contas/{args.tipo}/json/{os.path.basename(json_path)}")
    print(f"aws s3 cp \"{pdf_path}\"  s3://bantu-banco-da-nova-terra/contas/{args.tipo}/pdf/{os.path.basename(pdf_path)}")
    print(f"aws s3 cp \"{qr_path}\"   s3://bantu-banco-da-nova-terra/contas/{args.tipo}/qrcodes/{os.path.basename(qr_path)}")

if __name__ == "__main__":
    main()
