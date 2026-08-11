"""
Cria a tabela catalogo_produtos e insere todos os produtos do estoque OutletSIM.
Execute na VPS: python scripts/seed_catalogo.py
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
from dotenv import load_dotenv
load_dotenv()

DSN = os.getenv("DATABASE_URL", "postgresql://postgres:GIUasuiejaj82893_@localhost:5432/outletsim")

# (categoria, titulo, descricao, qtd, preco_venda)
PRODUTOS = [
    # ── Equipamentos Financeiros ──────────────────────────────────────────
    ("Equipamentos Financeiros", "Impressora de Cheques Chronos Check-Pronto", None, 1, 750.00),
    ("Equipamentos Financeiros", "Validadora de Cédulas Newton", None, 1, 4500.00),
    ("Equipamentos Financeiros", "Validadora de Cédulas Ntegra Compact", None, 1, 5000.00),

    # ── Telefonia ─────────────────────────────────────────────────────────
    ("Telefonia", "Aparelho Telefônico Digital Alcatel Lucent 4029", None, 10, 150.00),
    ("Telefonia", "Telefone Alcatel Lucent 4038", None, 1, 350.00),
    ("Telefonia", "Telefone Yealink T23G (POE)", None, 3, 200.00),
    ("Telefonia", "Telefone Yealink IP SIP T19 E2", None, 1, 150.00),
    ("Telefonia", "Telefone Avaya E129 SIP Deskphone", None, 2, 150.00),
    ("Telefonia", "Telefone Avaya 9608G", None, 46, 350.00),
    ("Telefonia", "Terminal IP X3SP Fanvil", None, 10, 250.00),
    ("Telefonia", "Telefone Fanvil X3Sg", None, 1, 250.00),
    ("Telefonia", "Telefone Fanvil X1 POE", None, 16, 150.00),
    ("Telefonia", "Terminal Inteligente Intelbras TI 5000", None, 2, 750.00),
    ("Telefonia", "Terminal Executivo Intelbras TE 220", None, 1, 200.00),
    ("Telefonia", "Telefone Intelbras TIP 200 LITE", None, 3, 100.00),
    ("Telefonia", "Telefone Grandstream GXP1610", None, 9, 150.00),
    ("Telefonia", "Telefone Grandstream GXP1630", None, 1, 200.00),
    ("Telefonia", "Telefone Grandstream IP/SIP GXP 2170", None, 7, 500.00),
    ("Telefonia", "Telefone Grandstream GRP2604P", None, 6, 250.00),
    ("Telefonia", "Telefone Grandstream BudgeTone-100", None, 1, 75.00),
    ("Telefonia", "Telefone Sem Fio Digital Intelbras TS40ID", "Com Identificação de Chamadas", 1, 100.00),
    ("Telefonia", "Interfone Intelbras TDMI300", None, 6, 75.00),
    ("Telefonia", "Telefone Intelbras Pleno", None, 3, 30.00),
    ("Telefonia", "Headset Intelbras HSB50", None, 1, 90.00),
    ("Telefonia", "Gateway Tradutor de Protocolos KMG MS Khomp", None, 1, 7500.00),
    ("Telefonia", "UMG Modulo Server 300 Khomp", "Com 1 Placa E1 com conector BNC", 1, 2000.00),
    ("Telefonia", "Gravador de Chamada Telefônica Sentinela Utech", None, 1, 5000.00),
    ("Telefonia", "UTECH Media Gateway Analógico-SIP (VoIP) MGA-04HI 4FXO", "Modular, 4 troncos FXO", 1, 1900.00),
    ("Telefonia", "ATA UTECH Gateway Analógico MAT-41E", "4 portas FXS para ramais, 1 porta FXO para tronco", 1, 300.00),
    ("Telefonia", "PABX Digistar XIP 230 PLUS (Config A)", "3 Placas Ramal 4, 4 Placas Interface Celular 1Ch, 2 Placas tronco 2", 1, 3000.00),
    ("Telefonia", "PABX Digistar XIP 230 PLUS (Config B)", "1 placa tronco, 5 Placas Ramais 4, 4 placas GSM Interface Celular, 1 Placa tronco 2", 1, 3000.00),
    ("Telefonia", "PABX Digistar XIP 230 PLUS (Config C)", "3 Placas Ramal 4, 1 Placa Tronco Ramal, 4 Placas Interface Celular 1Ch, 1 Placa tronco 2", 1, 1000.00),
    ("Telefonia", "Central Telefônica PABX Intelbras Corp 16000", None, 1, 5000.00),
    ("Telefonia", "Central Telefônica PABX Intelbras Remote", None, 1, 700.00),
    ("Telefonia", "Central PABX Digistar XIP 270 (Config Completa)", "1 Placa Interface Celular 4 canais GSM, 1 Placa 1E1 4 FXO, 3 Placas Ramal 16 FXS (48 ramais)", 1, 5000.00),
    ("Telefonia", "Central XIP 500 Digistar", None, 1, 3000.00),
    ("Telefonia", "Central PABX Digistar XIP 270", None, 1, 1000.00),
    ("Telefonia", "Telefone PABX Digistar KD-300 + Fio de Telefone", None, 1, 100.00),
    ("Telefonia", "Talkman A500 Wearable Device", None, 20, 1000.00),
    ("Telefonia", "Central IP Intelbras CIP 850", "S/FXS S/FXO", 1, 1500.00),
    ("Telefonia", "Módulo de Controle Alcatel Lucent 7750 SR CPM5", None, 1, 10000.00),

    # ── Body Cam ──────────────────────────────────────────────────────────
    ("Body Cam", "Bodycam Powerconn (Coelba) Modelo 1", None, 27, 300.00),
    ("Body Cam", "Bodycam Forttis Modelo 2", None, 11, 300.00),
    ("Body Cam", "Bodycam FP4 Forttis Modelo 3", None, 76, 300.00),
    ("Body Cam", "Bodycam Forttis Modelo 4", None, 37, 300.00),
    ("Body Cam", "Bodycam Powerconn TX-5PL", None, 19, 300.00),
    ("Body Cam", "Base Carregadora 8 Docas para Bodycam Modelo 1", None, 7, 1000.00),
    ("Body Cam", "Doca da Bodycam FP4 Forttis Modelo 3", None, 88, 100.00),
    ("Body Cam", "Doca da Bodycam Forttis Modelo 4", None, 69, 100.00),
    ("Body Cam", "Doca da Bodycam Powerconn TX-5PL", None, 19, 100.00),

    # ── Memórias ──────────────────────────────────────────────────────────
    ("Memórias", "Memória DDR3 SDRAM 4GB", None, 41, 65.00),
    ("Memórias", "Memória DDR3 SDRAM 8GB", None, 278, 130.00),
    ("Memórias", "Memória DDR3 SDRAM 16GB", None, 85, 275.00),
    ("Memórias", "Memória DDR3 SDRAM 2GB", None, 36, 35.00),
    ("Memórias", "Memória DDR2 PC2-5300F 1GB", None, 4, 30.00),
    ("Memórias", "Memória DDR2 PC2-5300F 4GB", None, 1, 90.00),
    ("Memórias", "Memória DDR3L SDRAM 32GB", None, 17, 300.00),

    # ── HD/SSD ────────────────────────────────────────────────────────────
    ("HD/SSD", "SSD SAS 800GB Tipo 2,5\"", None, 8, 2100.00),
    ("HD/SSD", "SSD SAS 400GB Tipo 2,5\"", None, 3, 1600.00),
    ("HD/SSD", "HD SAS 1.8TB Tipo 2,5\"", None, 12, 1100.00),
    ("HD/SSD", "HD SAS 900GB Tipo 2,5\"", None, 27, 800.00),
    ("HD/SSD", "HD SAS 146GB Tipo 2,5\"", None, 20, 225.00),
    ("HD/SSD", "HD SAS 500GB Tipo 2,5\"", None, 12, 325.00),
    ("HD/SSD", "HD SAS 300GB Tipo 2,5\"", None, 44, 275.00),
    ("HD/SSD", "HD SAS 600GB Tipo 2,5\"", None, 156, 325.00),
    ("HD/SSD", "SSD SAS 960GB Tipo 2,5\"", None, 4, 2400.00),
    ("HD/SSD", "SSD SAS 100GB Tipo 2,5\"", None, 2, 800.00),
    ("HD/SSD", "HD SAS 1.2TB Tipo 2,5\"", None, 3, 1200.00),
    ("HD/SSD", "HD SAS 72GB Tipo 2,5\"", None, 4, 200.00),
    ("HD/SSD", "HD SAS 73GB Tipo 2,5\"", None, 4, 200.00),
    ("HD/SSD", "HD SAS 2TB Tipo 2,5\"", None, 5, 1700.00),
    ("HD/SSD", "HD SAS 73GB Tipo 3,5\"", None, 1, 450.00),
    ("HD/SSD", "HD SAS 146GB Tipo 3,5\"", None, 2, 600.00),
    ("HD/SSD", "HD SAS 300GB Tipo 3,5\"", None, 2, 750.00),
    ("HD/SSD", "HD SAS 500GB Tipo 3,5\"", None, 1, 900.00),
    ("HD/SSD", "HD SAS 600GB Tipo 3,5\"", None, 3, 1000.00),
    ("HD/SSD", "HD SAS 8TB Tipo 3,5\"", None, 1, 2390.00),

    # ── Firewall ──────────────────────────────────────────────────────────
    ("Firewall", "Firewall Sophos XGS 107", None, 9, 1500.00),
    ("Firewall", "Firewall Sophos XGS 136", None, 1, 3000.00),
    ("Firewall", "Firewall Sophos XGS 2100", None, 2, 5000.00),
    ("Firewall", "Firewall Sophos XG230", None, 1, 2000.00),
    ("Firewall", "Firewall Sophos XG210", None, 1, 1500.00),
    ("Firewall", "Firewall Sophos XG135", None, 1, 1200.00),
    ("Firewall", "Firewall Sophos XG 125 Rev 3", None, 3, 1000.00),
    ("Firewall", "Firewall Sophos XG330", None, 1, 3000.00),
    ("Firewall", "Firewall Sophos SG 105 Rev 2", None, 4, 700.00),
    ("Firewall", "Sophos RED 50 Rev 1", "Remote Ethernet Device / Appliance de Segurança", 1, 600.00),
    ("Firewall", "Sophos RED 15 Rev 1", "Remote Ethernet Device / Appliance de Segurança", 1, 500.00),
    ("Firewall", "Fortgate 600E", None, 1, 15000.00),
    ("Firewall", "SonicWall SOHO Transmissão de Dados", None, 1, 500.00),
    ("Firewall", "Firewall SonicWall TZ-400", None, 1, 4000.00),
    ("Firewall", "Firewall SonicWall TZ-350", None, 6, 2500.00),
    ("Firewall", "Firewall SonicWall TZ-600", None, 3, 2500.00),
    ("Firewall", "SonicWall NSa 5650 NGFW", "Firewall de próxima geração (NGFW)", 1, 15000.00),
    ("Firewall", "Appliance de Segurança WatchGuard Firebox", None, 1, 2500.00),
    ("Firewall", "Appliance de Rede F5 Networks BIG-IP I7000 Series", None, 1, 50000.00),

    # ── Conferência ───────────────────────────────────────────────────────
    ("Conferência", "Câmera de Videoconferência Logitech", None, 5, 5000.00),
    ("Conferência", "Audioconferência GrandStream GAC 2500", None, 2, 1500.00),
    ("Conferência", "Video Conferência Yealink VC500 PRO", "Phone + 2 Microfones inclusos", 2, 10000.00),
    ("Conferência", "Video Conferência Yealink VC800", None, 1, 10000.00),
    ("Conferência", "Video Conferência Yealink VC200 + Phone CP960", None, 2, 6000.00),

    # ── Coletor de Dados ──────────────────────────────────────────────────
    ("Coletor de Dados", "Coletor de Dados Option H27", None, 8, 2000.00),
    ("Coletor de Dados", "Coletor de Dados Chainway C-61", None, 1, 3000.00),
    ("Coletor de Dados", "Coletor de Dados Compex AutoIDQ7", None, 8, 3000.00),
    ("Coletor de Dados", "Coletor de Dados Seuic AutoIDQ7", None, 4, 3000.00),
    ("Coletor de Dados", "Coletor de Dados Datalogic Memor1", None, 4, 3000.00),
    ("Coletor de Dados", "Coletor de Dados Seuic AutoID6LW", None, 8, 3000.00),
    ("Coletor de Dados", "Coletor Intermec CN70e NI", None, 4, 3000.00),
    ("Coletor de Dados", "Coletor de Dados Chainway C6000", None, 8, 3000.00),
    ("Coletor de Dados", "Coletor de Dados Datalogic ScorpioX4", None, 13, 3000.00),
    ("Coletor de Dados", "Coletor de Dados Point Mobile PM85", None, 5, 3000.00),
    ("Coletor de Dados", "Coletor de Dados Urovo DT40", None, 5, 3000.00),
    ("Coletor de Dados", "Coletor de Dados Symbol / Zebra MC32N0", None, 65, 3000.00),
    ("Coletor de Dados", "Leitor de Código de Barras LN 350 Linear-HCS", None, 2, 3000.00),

    # ── Segurança e CFTV ──────────────────────────────────────────────────
    ("Segurança e CFTV", "Bastão de Ronda Active Track EBS", None, 32, 500.00),
    ("Segurança e CFTV", "DVR Hikvision DS-7204 4CH", None, 4, 250.00),
    ("Segurança e CFTV", "DVR TWG 5104 4ch", None, 1, 250.00),
    ("Segurança e CFTV", "DVR Hikvision DS-7216HQHI-F2/N 16 Canais", None, 5, 400.00),
    ("Segurança e CFTV", "DVR Hikvision DS-7216HQHI-K2 16 Canais", None, 13, 450.00),
    ("Segurança e CFTV", "NVR Hikvision DS-7616NIQ1 16 Canais", None, 2, 500.00),
    ("Segurança e CFTV", "NVR Hikvision DS-7616NIE2 16 Canais", None, 1, 500.00),
    ("Segurança e CFTV", "NVR 3S Security S2560", None, 1, 500.00),
    ("Segurança e CFTV", "MDVR V2 Tech 04 CH AHD/SD", None, 4, 2000.00),
    ("Segurança e CFTV", "MDVR Tecno Mobile ITS-4CH-SD", None, 3, 600.00),
    ("Segurança e CFTV", "MDVR VTX 300", None, 7, 900.00),
    ("Segurança e CFTV", "MVD Intelbras 3404 GW Série 3000", None, 19, 500.00),
    ("Segurança e CFTV", "Central de Cerca Elétrica JFL Alarmes ECR-8 Plus", None, 1, 150.00),
    ("Segurança e CFTV", "Central de Alarme JFL SmartCloud18", None, 1, 250.00),
    ("Segurança e CFTV", "Central de Alarme AMT2118 EG", None, 2, 400.00),
    ("Segurança e CFTV", "Central de Alarme Viaweb System 16z com Teclado Touch Screen", None, 1, 300.00),
    ("Segurança e CFTV", "Antena Intelbras LE 150 EP", None, 1, 1500.00),
    ("Segurança e CFTV", "Antena Veicular Leitor de TAG LE 170 Intelbras", None, 1, 2000.00),
    ("Segurança e CFTV", "Motor de Portão PPA Jet Flex Deslizante DZ 800", None, 1, 400.00),
    ("Segurança e CFTV", "Câmera Hikvision DS-2CD1023G0E-I", None, 2, 200.00),
    ("Segurança e CFTV", "Câmera Bullet Hickmicro HMTD26288QABR", None, 1, 500.00),
    ("Segurança e CFTV", "Câmera AHD Full HD Intelbras VMH 1220 B", None, 5, 50.00),
    ("Segurança e CFTV", "Câmera Bullet Multi HD Intelbras VHD 3140 VF G4", None, 5, 150.00),
    ("Segurança e CFTV", "Câmera Bullet Intelbras VIPS3330G2", None, 4, 150.00),
    ("Segurança e CFTV", "Câmera Intelbras 1120", None, 16, 50.00),
    ("Segurança e CFTV", "Intelbras VB1016WP Power Balun para Câmeras 16 Canais", None, 1, 675.00),
    ("Segurança e CFTV", "Câmera Bullet TWG Instruseg", None, 12, 60.00),
    ("Segurança e CFTV", "Switch PoE 8 Portas com 2 UpLink TWG", None, 2, 200.00),
    ("Segurança e CFTV", "Par de Conversores de Mídia Fibra Óptica FiberWan FWE2-111", "Fast Ethernet 10/100 Mbps Híbrido", 1, 200.00),
    ("Segurança e CFTV", "Conversor de Mídia Fast Intelbras KFSD1120 B", None, 2, 150.00),
    ("Segurança e CFTV", "Câmera Veicular Dupla 2ch 1080p HD Para DVR", None, 1, 420.00),
    ("Segurança e CFTV", "Câmera IP 1080p Wifi Full HD Externa e Interna (Grava em SD)", None, 2, 200.00),
    ("Segurança e CFTV", "Câmera 1080P Sem Fio com Lâmpada de LED", None, 2, 390.00),
    ("Segurança e CFTV", "Câmera Filmadora Veicular com Câmera de Ré - Komprei", None, 1, 350.00),
    ("Segurança e CFTV", "DVR Filmadora e Câmera Veicular 2 Lentes - Komprei", None, 5, 350.00),
    ("Segurança e CFTV", "Giroflex Strobo 86 Leds Amarelo x Branco (Quebra-sol)", None, 8, 250.00),
    ("Segurança e CFTV", "Giroflex Strobo 132 Leds Vermelho x Vermelho para Viaturas", None, 20, 250.00),
    ("Segurança e CFTV", "Placas de LED Amarelo Quadrada", None, 124, 100.00),
    ("Segurança e CFTV", "Câmera Veicular", None, 1, 250.00),
    ("Segurança e CFTV", "Monitor CAR TFT-LED", None, 1, 250.00),
    ("Segurança e CFTV", "Rastreador Veicular", None, 1, 240.00),
    ("Segurança e CFTV", "Roteador TP-Link TL-R470T+ Load Balance", None, 1, 149.99),

    # ── Controle de Acesso ────────────────────────────────────────────────
    ("Controle de Acesso", "Módulo GPRS XG 4000 Smart Intelbras", None, 1, 200.00),
    ("Controle de Acesso", "Controlador de Acesso Intelbras SS3530 MF Face", None, 3, 500.00),
    ("Controle de Acesso", "Controladora de Acesso Facial Intelbras SS1530 MF W", None, 1, 500.00),
    ("Controle de Acesso", "Receptor Multifunção 4A", None, 8, 300.00),
    ("Controle de Acesso", "Video Porteiro IP Intelbras TVIP 500 HF", None, 8, 400.00),
    ("Controle de Acesso", "Sensor Intelbras IVA-3015X", None, 2, 125.00),
    ("Controle de Acesso", "Controlador de Acesso Intelbras CT 500 1P", None, 2, 500.00),
    ("Controle de Acesso", "Controlador Linear Digital de Acesso LN5-P Anviz", None, 3, 300.00),
    ("Controle de Acesso", "Porteiro Eletrônico Intelbras XPE 1013 Plus", None, 2, 150.00),
    ("Controle de Acesso", "Video Porteiro IP Intelbras XPE3101", None, 1, 1000.00),
    ("Controle de Acesso", "Controle Facial Intelbras XPE 3200 IP Face", None, 1, 1250.00),
    ("Controle de Acesso", "Controlador Facial Intelbras SS 3532MF", None, 1, 800.00),
    ("Controle de Acesso", "Controlador de Acesso Facial Control iD iDFace (Face Prox ASK)", None, 2, 800.00),
    ("Controle de Acesso", "Leitor Biométrico Control ID Flex V2 IP65", None, 1, 600.00),
    ("Controle de Acesso", "Video Porteiro IP Intelbras PVIP 1000", "Obs: frontal danificado", 1, 1000.00),
    ("Controle de Acesso", "Registrador Eletrônico de Ponto Pointline RWTech", None, 2, 900.00),
    ("Controle de Acesso", "ZK inBio-460 Controladora de Acesso 4 Portas", "Para até 8 leitoras biométricas e/ou proximidade", 4, 1000.00),
    ("Controle de Acesso", "Central Intelbras CP 112 (Somente a Base)", None, 1, 1000.00),
    ("Controle de Acesso", "Controlador de Acesso Utech MPI-21EB", None, 9, 1000.00),
    ("Controle de Acesso", "Painel de Controle AVA PRO CPX300W EBS", "GSM/GPRS, RF 868Mhz, 8 zonas com fio e 64 sem fio, inclui Gabinete EBS", 11, 1500.00),
    ("Controle de Acesso", "Módulo Guarita", None, 2, 360.00),
    ("Controle de Acesso", "Módulo Inteligente de Portaria IP MIP1000", None, 1, 350.00),
    ("Controle de Acesso", "Hikvision Controle de Acesso Facial Termográfico DS-K1TA70MI-T", None, 2, 2000.00),
    ("Controle de Acesso", "Controlador de Acesso Facial Intelbras SS 3530 MF Face", None, 3, 500.00),
    ("Controle de Acesso", "Leitor Facial ZKteco V4L para 800 Faces", "Semi novo", 1, 1000.00),
    ("Controle de Acesso", "Receptor RTX 3004 Linear Nice", None, 1, 300.00),
    ("Controle de Acesso", "Receptor Wiegand CTW-4A", None, 1, 320.00),
    ("Controle de Acesso", "Fechadura Eletroímã 150 KGF FE 22150", None, 2, 200.00),
    ("Controle de Acesso", "Botoeira de Saída Virdi", None, 2, 100.00),
    ("Controle de Acesso", "Sensor de Barreira Ativo JFL IRA 315 Digital", None, 12, 70.00),
    ("Controle de Acesso", "Sensor de Barreira Ativo JFL IRA 115 Digital", None, 2, 50.00),
    ("Controle de Acesso", "Sensor de Barreira Intelbras IVA 3070X", None, 5, 250.00),
    ("Controle de Acesso", "Fechadura Eletroímã 300 KGF com Sensor FE10300", None, 1, 300.00),
    ("Controle de Acesso", "Sensor Infravermelho Ativo Intelbras IVA 7100 Dual", None, 8, 250.00),

    # ── Áudio Visual ──────────────────────────────────────────────────────
    ("Áudio Visual", "Projetor Christie DHD775-E", None, 4, 15000.00),
    ("Áudio Visual", "Máquina Arcade Dupla Profissional – Pandora Box", None, 1, 12500.00),
    ("Áudio Visual", "Mesa de Som Digital Yamaha MGX12", None, 1, 5990.00),

    # ── Casa, Móveis e Decoração ──────────────────────────────────────────
    ("Casa, Móveis e Decoração", "Tapete Arajuta by Kamy", "Índia, Cor Dune, 80% Juta 20% Algodão, 3,50 × 2,55 m (8,92 m²)", 1, 2250.00),
    ("Casa, Móveis e Decoração", "Tapete Esmeralda TAPETAH", "3,60 × 5,00 m", 1, 5400.00),
    ("Casa, Móveis e Decoração", "Tapete Verde Juta by Kamy Mix Petróleo Zili Juta1", "4,04 × 3,06 m (12 m²)", 1, 3000.00),
    ("Casa, Móveis e Decoração", "Cadeira de Jantar", None, 4, 645.00),
    ("Casa, Móveis e Decoração", "Sofá Gomos Lider Interiores Suite Design", None, 1, 5000.00),
    ("Casa, Móveis e Decoração", "Mesa Redonda 2m em Madeira Cumaru com Centro Giratório de Alumínio", "Nova", 1, 8500.00),
]


def main():
    conn = psycopg2.connect(DSN)
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS catalogo_produtos (
                        id          SERIAL PRIMARY KEY,
                        categoria   VARCHAR(100) NOT NULL,
                        titulo      TEXT NOT NULL,
                        descricao   TEXT,
                        qtd         INTEGER NOT NULL DEFAULT 0,
                        preco_venda NUMERIC(12, 2),
                        foto_url    TEXT,
                        ativo       BOOLEAN NOT NULL DEFAULT TRUE,
                        criado_em   TIMESTAMP DEFAULT NOW()
                    )
                """)
                print("✓ Tabela catalogo_produtos OK")

                cur.execute("SELECT COUNT(*) FROM catalogo_produtos")
                count = cur.fetchone()[0]
                if count > 0:
                    resp = input(f"  Já existem {count} produtos. Limpar e re-inserir? [s/N] ")
                    if resp.strip().lower() != "s":
                        print("Abortado.")
                        return
                    cur.execute("TRUNCATE TABLE catalogo_produtos RESTART IDENTITY")
                    print("  Tabela limpa.")

                cur.executemany("""
                    INSERT INTO catalogo_produtos (categoria, titulo, descricao, qtd, preco_venda)
                    VALUES (%s, %s, %s, %s, %s)
                """, PRODUTOS)
                print(f"✓ {len(PRODUTOS)} produtos inseridos com sucesso!")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
