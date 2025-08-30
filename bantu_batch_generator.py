#!/usr/bin/env python3
import os, csv, re, json, hashlib, datetime, unicodedata
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.graphics.barcode import qr as qrmod
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPM

VALID_TYPES = {"cliente","ministerio","levita","governo","investidor"}
ADDR_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")

def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def slugify(text: str) -> str:
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
    text = re.sub(r"[^a-zA-Z0-9\-]+", "-", text.strip().lower()).strip("-")
    text = re.sub(r"-{2,}", "-", text)
    return text or "conta"

def ensure_dirs(*dirs):
    for d in dirs:
        Path(d).mkdir(parents=True, exist_ok=True)

def make_qr_png(text: str, png_path: str, size_px: int = 512):
    widget = qrmod.QrCodeWidget(text)
    x0, y0, x1, y1 = widget.getBounds()
    w, h = (x1 - x0), (y1 - y0)
    scale = float(size_px) / max(w, h)
    d = Drawing(size_px, size_px, transform=[scale, 0, 0, scale, 0, 0])
    d.add(widget)
    renderPM.drawToFile(d, png_path, fmt="PNG")

def make_pdf(model: dict, pdf_path: str, qr_png_path: str, signature_img: str = None):
    width, height = A4
    c = canvas.Canvas(pdf_path, pagesize=A4)
    left = 20*mm; right = width - 20*mm; top = height - 20*mm; bottom = 20*mm

    # Header
    c.setFillColorRGB(0.05, 0.09, 0.16)
    c.rect(0, height - 40*mm, width, 40*mm, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(width/2, height - 20*mm, "BANTU — Registro de Conta")
    c.setFont("Helvetica", 10)
    c.drawCentredString(width/2, height - 29*mm, "Banco da Nova Terra Universal • Documento Selado")
    c.drawCentredString(width/2, height - 34*mm, datetime.datetime.utcnow().strftime("Gerado em %Y-%m-%d %H:%M UTC"))

    # Body
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
    ap = argparse.ArgumentParser(description="BANTU — Gerador em Lote a partir de CSV")
    ap.add_argument("--csv", required=True, help="Caminho do CSV (UTF-8)")
    ap.add_argument("--out", required=True, help="Diretório base de saída (ex.: /mnt/data/bantu_generator/output)")
    ap.add_argument("--sig", default="", help="Imagem de assinatura (opcional)")
    ap.add_argument("--default-status", default="publico", choices=["publico","privado"], help="Status padrão se coluna 'status' vier vazia")
    ap.add_argument("--id-prefix", default="BANTU-", help="Prefixo de ID quando não houver 'id_conta' no CSV (ex.: BANTU-)")
    ap.add_argument("--start", type=int, default=1, help="Início da sequência numérica para IDs (quando gerados)")
    ap.add_argument("--pad", type=int, default=4, help="Zeros à esquerda para IDs (ex.: 4 -> BANTU-0001)")
    ap.add_argument("--use-csv-ids", action="store_true", help="Se presente, usa 'id_conta' do CSV quando existir; caso contrário, gera ID sequencial")
    args = ap.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        raise SystemExit(f"CSV não encontrado: {csv_path}")

    out_base = Path(args.out)
    ensure_dirs(out_base)

    ts = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    manifest = {
        "timestamp_utc": ts,
        "csv_source": str(csv_path),
        "results": []
    }
    upload_lines = []

    # sequence
    seq = args.start

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=1):
            nome = (row.get("nome") or "").strip()
            tipo = (row.get("tipo_conta") or "").strip().lower()
            addr = (row.get("endereco_evm") or "").strip()
            status = (row.get("status") or "").strip().lower() or args.default_status
            obs = (row.get("observacoes") or "").strip()
            cid = (row.get("id_conta") or "").strip()

            errors = []
            if not nome: errors.append("nome vazio")
            if tipo not in VALID_TYPES: errors.append(f"tipo_conta inválido: {tipo}")
            if not ADDR_RE.match(addr): errors.append(f"endereco_evm inválido: {addr}")
            if status not in {"publico","privado"}: errors.append(f"status inválido: {status}")

            if errors:
                manifest["results"].append({"row": i, "nome": nome, "tipo": tipo, "status": "ERRO", "errors": errors})
                continue

            # ID handling
            if args.use_csv_ids and cid:
                id_conta = cid
            else:
                id_conta = f"{args.id_prefix}{str(seq).zfill(args.pad)}"
                seq += 1

            safe = slugify(nome)
            tipo_dir = out_base / "contas" / tipo
            json_dir = tipo_dir / "json"
            pdf_dir = tipo_dir / "pdf"
            qr_dir = tipo_dir / "qrcodes"
            ensure_dirs(json_dir, pdf_dir, qr_dir)

            json_path = json_dir / f"{safe}.json"
            pdf_path  = pdf_dir / f"{safe}.pdf"
            qr_path   = qr_dir / f"{safe}.png"

            # Generate QR
            make_qr_png(addr, str(qr_path), size_px=512)

            # Build model
            sha = sha256_hex(addr)
            now_iso = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
            model = {
                "id_conta": id_conta,
                "nome": nome,
                "tipo_conta": tipo,
                "endereco_evm": addr,
                "hash_sha256": sha,
                "qrcode": str(qr_path),
                "status": status,
                "data_registro": now_iso,
                "observacoes": obs or "—",
                "assinatura_responsavel": "Kizequiel Guilherme Nzau – Servo do Senhor, Responsável terreno da Obra",
                "documentos": {
                    "pdf_selado": str(pdf_path),
                    "json_original": str(json_path)
                }
            }

            # Save JSON/PDF
            with open(json_path, "w", encoding="utf-8") as jf:
                json.dump(model, jf, ensure_ascii=False, indent=2)
            make_pdf(model, str(pdf_path), str(qr_path), signature_img=args.sig if args.sig else None)

            # Record
            manifest["results"].append({
                "row": i, "id_conta": id_conta, "nome": nome, "tipo": tipo, "status": "OK",
                "json": str(json_path), "pdf": str(pdf_path), "qrcode": str(qr_path)
            })
            upload_lines.extend([
                f'aws s3 cp "{json_path}" s3://bantu-banco-da-nova-terra/contas/{tipo}/json/{json_path.name}',
                f'aws s3 cp "{pdf_path}"  s3://bantu-banco-da-nova-terra/contas/{tipo}/pdf/{pdf_path.name}',
                f'aws s3 cp "{qr_path}"   s3://bantu-banco-da-nova-terra/contas/{tipo}/qrcodes/{qr_path.name}',
            ])

    # Write manifest and upload script
    manifest_path = out_base / f"manifest_{ts}.json"
    with open(manifest_path, "w", encoding="utf-8") as mf:
        json.dump(manifest, mf, ensure_ascii=False, indent=2)

    upload_sh = out_base / f"s3_upload_{ts}.sh"
    with open(upload_sh, "w", encoding="utf-8") as uf:
        uf.write("#!/usr/bin/env bash\nset -euo pipefail\n\n")
        for line in upload_lines:
            uf.write(line + "\n")
    os.chmod(upload_sh, 0o755)

    # Summary to stdout
    ok = sum(1 for r in manifest["results"] if r.get("status") == "OK")
    err = sum(1 for r in manifest["results"] if r.get("status") == "ERRO")
    print(f"Concluído. OK={ok}, ERROS={err}")
    print("Manifest:", manifest_path)
    print("Upload script:", upload_sh)

if __name__ == "__main__":
    main()
