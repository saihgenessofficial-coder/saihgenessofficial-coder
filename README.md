# BANTU — Banco da Nova Terra Universal · Automação (Python + AWS)

Automação prática para registro e transparência de contas do **BANTU** usando **Python** e **AWS S3**.

- **Gerador unitário**: cria **JSON + QR Code + PDF selado** para uma conta.  
- **Gerador em lote (CSV)**: processa centenas/milhares mantendo o mesmo padrão.  
- **Website S3**: `index.html` público com política de leitura seletiva; zona **privado/** permanece restrita.  
- **Segurança**: princípio do menor privilégio (**IAM**), hashes **SHA-256**, carimbo **UTC** e trilha de auditoria (*manifest*).

> Repositório: https://github.com/saihgenessofficial-coder/saihgenessofficial-coder

---

## 📦 Estrutura (sugerida)
```
bantu_generator/
├── bantu_account_generator.py      # gerador unitário (JSON + QR + PDF)
├── bantu_batch_generator.py        # gerador em lote (CSV → JSON/QR/PDF)
├── templates/
│   └── accounts_template.csv       # modelo de entrada
└── output/
    ├── contas/<tipo>/{json,pdf,qrcodes}/
    ├── manifest_YYYYMMDDTHHMMSSZ.json
    └── s3_upload_YYYYMMDDTHHMMSSZ.sh   # comandos prontos de upload
bantu_site/
├── index.html                      # página pública
├── error.html                      # página de erro
└── bucket_policy_public_read.json  # leitura pública seletiva (index/docs/contracts/publico)
```
Tipos de conta aceitos: `cliente | ministerio | levita | governo | investidor`.

---

## 🚀 Pré-requisitos
- **Python 3.9+**
- Bibliotecas: `pip install reportlab`
- **AWS CLI** configurada (`aws configure`, região `us-east-2`)
- Permissões **IAM** mínimas para `s3:PutObject`, `s3:GetObject`, `s3:DeleteObject` em `arn:aws:s3:::bantu-banco-da-nova-terra/privado/*` e `s3:ListBucket` com prefix `privado/*`.

---

## ▶️ Uso — Gerador **unitário**
```bash
python3 bantu_generator/bantu_account_generator.py   --id BANTU-0001   --nome "Igreja Trono e Glória"   --tipo ministerio   --address 0x0000000000000000000000000000000000000000   --out "bantu_generator/output/contas/ministerios"   --sig "KIZEQUIEL_ASSINATURA.jpg"           # opcional
```
Saída:
- `json/igreja-trono-e-gloria.json` (com **SHA-256** do endereço)  
- `qrcodes/igreja-trono-e-gloria.png`  
- `pdf/igreja-trono-e-gloria.pdf`

---

## ▶️ Uso — Gerador **em lote** (CSV)
**1) Edite o CSV** seguindo o template:
```csv
id_conta,nome,tipo_conta,endereco_evm,status,observacoes
BANTU-0001,Igreja Trono e Glória,ministerio,0x0000000000000000000000000000000000000000,publico,Conta oficial de ministério.
BANTU-0002,Zauquiel Divine Gates,levita,0x1111111111111111111111111111111111111111,publico,Conta de levita.
```
**2) Rode o gerador:**
```bash
python3 bantu_generator/bantu_batch_generator.py   --csv "bantu_generator/templates/accounts_template.csv"   --out "bantu_generator/output"   --sig "KIZEQUIEL_ASSINATURA.jpg"   --id-prefix BANTU- --start 1 --pad 4   --default-status publico   --use-csv-ids
```
Cria **JSON + QR + PDF** por linha e gera:
- `manifest_YYYYMMDDTHHMMSSZ.json` (resumo OK/ERRO)  
- `s3_upload_YYYYMMDDTHHMMSSZ.sh` (comandos `aws s3 cp` prontos)

---

## ☁️ Publicação no **S3**
Enviar páginas públicas (raiz do bucket):
```bash
aws s3 cp bantu_site/index.html s3://bantu-banco-da-nova-terra/index.html --content-type text/html
aws s3 cp bantu_site/error.html s3://bantu-banco-da-nova-terra/error.html --content-type text/html
```
**Política do bucket** (leitura pública seletiva):
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowPublicReadPublicoDocsContractsAndRootPages",
      "Effect": "Allow",
      "Principal": "*",
      "Action": ["s3:GetObject"],
      "Resource": [
        "arn:aws:s3:::bantu-banco-da-nova-terra/publico/*",
        "arn:aws:s3:::bantu-banco-da-nova-terra/docs/*",
        "arn:aws:s3:::bantu-banco-da-nova-terra/contracts/*",
        "arn:aws:s3:::bantu-banco-da-nova-terra/index.html",
        "arn:aws:s3:::bantu-banco-da-nova-terra/error.html"
      ]
    }
  ]
}
```
**Website (opcional, fallback 404 → index):**
`website.json`
```json
{
  "IndexDocument": { "Suffix": "index.html" },
  "ErrorDocument": { "Key": "error.html" },
  "RoutingRules": [
    { "Condition": { "HttpErrorCodeReturnedEquals": "404" },
      "Redirect": { "ReplaceKeyWith": "index.html" } }
  ]
}
```
Aplicar:
```bash
aws s3api put-bucket-website --bucket bantu-banco-da-nova-terra --website-configuration file://website.json
```

---

## 🔐 Notas de segurança
- **Privado ≠ Público**: só `index.html`, `error.html`, `docs/*`, `publico/*` e `contracts/*` têm leitura pública.  
- **IAM mínimo** para upload em `privado/*`.  
- **Sem chaves privadas** aqui; somente **endereços públicos EVM** e metadados.  
- (Opcional) **SSE-S3** ou **SSE-KMS** para criptografia em repouso.

---

## 🗺️ Roadmap
- Dockerfile e `make` helpers  
- Terraform para S3/IAM (infra como código)  
- Logs/relatórios de execução no manifest  
- Testes automatizados (PyTest)

---

## 🧾 Licença
MIT — use, cite e compartilhe.

## ✉️ Contato
Abra uma *issue* ou conecte-se pelo GitHub acima.
