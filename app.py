import os
import streamlit as st
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

st.set_page_config(
    page_title="貝拉の回信神器 | Problue",import os
import pprint
import streamlit as st
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

st.set_page_config(
    page_title="貝拉の回信神器 | Problue",
    page_icon="✉️",
    layout="wide",
)


def apply_custom_theme() -> None:
    st.markdown(
        """
        <style>
        .stApp { background-color: #FAF6F0; color: #2C2621; }
        .block-container { padding-top: 2rem; max-width: 1400px; }
        [data-testid="stSidebar"] {
            background-color: #F3ECE1;
            border-right: 1px solid #E2D6C5;
        }
        /* 卡片 */
        div[data-testid="stVerticalBlockBorderWrapper"] {
            background-color: #FFFDF9;
            border-color: #E2D6C5;
            border-radius: 14px;
        }
        /* 按鈕 */
        .stButton > button[kind="primary"] {
            background-color: #C87D4B;
            color: #FFFFFF;
            border: none;
            border-radius: 10px;
            padding: 0.6rem 1.2rem;
            font-weight: 600;
        }
        .stButton > button[kind="primary"]:hover { background-color: #B26A3B; }
        .stButton > button:not([kind="primary"]) {
            border-radius: 10px;
            border: 1px solid #D8C7B2;
            background-color: #FFFDF9;
            color: #2C2621;
        }
        /* 分頁 */
        .stTabs [data-baseweb="tab"] { font-weight: 600; }
        .stTabs [data-baseweb="tab-list"] { gap: 0.5rem; }
        /* 卡片標題 */
        .card-title { font-size: 1.05rem; font-weight: 700; margin-bottom: 0.4rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )


apply_custom_theme()

FIXED_GUARDRAILS_ZH = [
    "訂單若已準備好，只寫 ready（訂單已備妥），絕對不要自行加上 ahead of schedule、early 或提早完成。",
    "運費若是 Bella 幫忙查詢提供的，清楚說明運費由我方協助查詢提供，待確認寄送方式後提供明細或選項。",
    "單據名稱嚴格依指令或重點指定：若只提到 Invoice，就只寫 Invoice，不要自行加上 Commercial Invoice。",
    "所有事實皆以勾選項目、主管建議與補充說明為準，不自行腦補交期、折扣、庫存量或付款條件。",
    "聯絡人的「內部職位／備註」僅供 Bella 內部辨識與參考，絕對不要寫進寄給客戶或廠商的英文信件內文。",
    "英文回信結尾統一以 Bella（Sales Assistant | Problue）署名；若涉及公司基本資料，使用 PROBLUE INTERNATIONAL CORP.、NO. 32-28, LN. 1, SEC. 2, MINZU RD., TANZI DIST., TAICHUNG 427, TAIWAN、TEL: 04-25689717。",
]

# 結構：CONTACTS_DB[客戶分類][客戶公司名稱 / 貨代 / 快遞][國家][聯絡人姓名]
DEFAULT_CONTACTS_DB: dict[str, dict[str, dict[str, dict[str, dict[str, str]]]]] = {
    "海外": {
        "Mireya Corp.": {
            "西班牙": {
                "Mireya": {
                    "salutation": "Hi Mireya",
                    "internal_title": "西班牙主要採購與帳務對接窗口",
                    "default_notes": "長線合作客戶；分項訂單與未付餘額需列明細表核對，付款後請附匯款水單。",
                },
                "Carlos": {
                    "salutation": "Hi Carlos",
                    "internal_title": "西班牙倉庫 / 收貨窗口",
                    "default_notes": "主要對接收貨與箱單確認。",
                },
            }
        },
        "Luke Marine Supply": {
            "美國": {
                "Luke": {
                    "salutation": "Dear Luke",
                    "internal_title": "美國採購窗口 / 習慣信用卡付款",
                    "default_notes": "付款習慣簽回 Credit Card Authorization Form；海關申報發票比照先前需求以每件 USD 2.00 申報。",
                }
            }
        },
        "Chris Diving Co.": {
            "美國": {
                "Chris": {
                    "salutation": "Dear Chris",
                    "internal_title": "美國客戶窗口 / 運費多刷卡",
                    "default_notes": "運費多建議對方使用信用卡並簽回 Credit Card Authorization Form。",
                }
            }
        },
        "Jay Ocean Gear": {
            "美國": {
                "Jay": {
                    "salutation": "Hi Jay",
                    "internal_title": "美國詢價窗口",
                    "default_notes": "需比較不同快遞運費與預估天數供挑選。",
                }
            }
        },
    },
    "貨代": {
        "Joel Parnes Logistics": {
            "台灣 / 國際": {
                "Joel Parnes": {
                    "salutation": "Hi Joel Parnes",
                    "internal_title": "主要貨代窗口（Forwarder）",
                    "default_notes": "需附 Invoice 與 Packing List，並提供 Problue 完整公司地址與電話。",
                }
            }
        }
    },
    "快遞": {
        "UPS": {
            "台灣 / 全球": {
                "UPS 客服 / 取件窗口": {
                    "salutation": "Hi UPS Team",
                    "internal_title": "快遞公司 - UPS",
                    "default_notes": "確認取件時間、追蹤單號或運費報價。",
                }
            }
        },
        "FedEx": {
            "台灣 / 全球": {
                "FedEx 客服 / 取件窗口": {
                    "salutation": "Hi FedEx Team",
                    "internal_title": "快遞公司 - FedEx",
                    "default_notes": "確認取件時間、追蹤單號或運費報價。",
                }
            }
        },
        "DHL": {
            "台灣 / 全球": {
                "DHL 客服 / 取件窗口": {
                    "salutation": "Hi DHL Team",
                    "internal_title": "快遞公司 - DHL",
                    "default_notes": "確認取件時間、追蹤單號或運費報價。",
                }
            }
        },
    },
}

ACTION_MODULES = [
    {
        "id": "goods_ready",
        "label": "📦 貨物已準備好（Ready）",
        "prompt_zh": "通知對方貨物已經準備好了（只寫 ready，不要寫提早完成）。",
    },
    {
        "id": "ask_payment",
        "label": "💰 請對方付款 / 匯款",
        "prompt_zh": "請對方安排支付款項或尾款。",
    },
    {
        "id": "confirm_payment",
        "label": "✅ 確認已收到款項",
        "prompt_zh": "感謝對方迅速安排付款，向對方確認我方已收到款項。",
    },
    {
        "id": "cc_auth_form",
        "label": "💳 請簽回信用卡授權書",
        "prompt_zh": "附上載有先前提供之信用卡資訊的 Credit Card Authorization Form，請對方確認細節、簽名並回傳以便扣款與安排出貨。",
    },
    {
        "id": "courier_quote",
        "label": "🚚 提供快遞運費選項",
        "prompt_zh": "列出各快遞選項的預估天數與費用供挑選（註明實際送達時間視當地情況而定）。",
    },
    {
        "id": "shipped_tracking",
        "label": "✈️ 通知貨已寄出 / 已取件",
        "prompt_zh": "通知對方貨物已寄出／快遞已完成取件，並祝對方順利收到貨物。",
    },
    {
        "id": "invoice_only",
        "label": "📄 確認後只開 Invoice",
        "prompt_zh": "說明確認後我方會開立 Invoice（只寫 Invoice，不要寫 Commercial Invoice）。",
    },
    {
        "id": "contact_forwarder",
        "label": "🏭 貨代提貨＋附公司資料",
        "prompt_zh": "通知貨物已備妥並附上單據，提供 Problue 完整公司英文地址與電話，請提早提供空運或取件細節。",
    },
]

COMMON_DETAIL_MODULES = [
    {
        "id": "det_freight_checked_by_us",
        "label": "🔍 運費是我幫她查的",
        "prompt_zh": "清楚說明此運費報價是由我方協助查詢整理的。",
    },
    {
        "id": "det_wire_slip",
        "label": "🧾 請提供匯款水單",
        "prompt_zh": "請對方於完成匯款後提供匯款水單（bank wire slip）以便我方財務核對。",
    },
    {
        "id": "det_cc_faster_ship",
        "label": "⚡ 建議刷卡以便盡快出貨",
        "prompt_zh": "建議對方可使用信用卡支付並簽回授權書，以便我方能更快速安排出貨。",
    },
    {
        "id": "det_quote_valid_1wk",
        "label": "⏳ 運費報價有效期一週",
        "prompt_zh": "備註以上運費報價有效期為一週（valid for one week）。",
    },
    {
        "id": "det_usd2_customs",
        "label": "🏷️ 海關申報每件 USD 2.00",
        "prompt_zh": "海關申報發票比照先前需求以每件 USD 2.00（USD 2.00 per piece）申報。",
    },
    {
        "id": "det_goods_paid_freight_due",
        "label": "💵 貨款已收，僅剩運費未付",
        "prompt_zh": "說明貨款部分我方已收到，目前僅剩運費金額待支付。",
    },
    {
        "id": "det_tracking_attached",
        "label": "🔢 附追蹤單號（見補充欄）",
        "prompt_zh": "在信中清楚附上本次提供的快遞追蹤單號（Tracking Number）供查詢。",
    },
    {
        "id": "det_attach_inv_pl",
        "label": "📎 已附 Invoice & Packing List",
        "prompt_zh": "說明已隨信附上 Invoice 與 Packing List 供核對與安排。",
    },
]


def _deep_copy_db(db: dict) -> dict:
    return {
        cat: {
            sub: {
                country: {person: info.copy() for person, info in people.items()}
                for country, people in countries.items()
            }
            for sub, countries in subs.items()
        }
        for cat, subs in db.items()
    }


def format_order_code(po_raw: str, b2pt_raw: str) -> str:
    po = po_raw.strip()
    b2pt = b2pt_raw.strip()

    if po and not po.upper().startswith("PO#"):
        po_formatted = f"PO#{po}"
    else:
        po_formatted = po

    if b2pt and not b2pt.upper().startswith("B2PT"):
        b2pt_formatted = f"B2PT{b2pt}"
    else:
        b2pt_formatted = b2pt

    if po_formatted and b2pt_formatted:
        return f"{po_formatted}({b2pt_formatted})"
    if po_formatted:
        return po_formatted
    if b2pt_formatted:
        return b2pt_formatted
    return ""


# ================= UI 小工具 =================
def show_code(text: str) -> None:
    """顯示可一鍵複製的文字；新版 Streamlit 自動換行，舊版自動退回。"""
    try:
        st.code(text, language=None, wrap_lines=True)
    except TypeError:
        st.code(text, language=None)


def multi_pick(label: str, modules: list[dict], key: str) -> list[str]:
    """以標籤按鈕（pills）複選；版本過舊時退回 multiselect。回傳選中項目的 prompt_zh。"""
    mapping = {m["label"]: m["prompt_zh"] for m in modules}
    if hasattr(st, "pills"):
        picked = st.pills(label, list(mapping), selection_mode="multi", key=key)
    else:
        picked = st.multiselect(label, list(mapping), key=key)
    return [mapping[k] for k in (picked or [])]


def card_title(text: str) -> None:
    st.markdown(f'<div class="card-title">{text}</div>', unsafe_allow_html=True)


# ================= 初始化 Session State =================
if "contacts_db" not in st.session_state:
    st.session_state["contacts_db"] = _deep_copy_db(DEFAULT_CONTACTS_DB)
if "salutation_val" not in st.session_state:
    st.session_state["salutation_val"] = ""
if "last_reply_result" not in st.session_state:
    st.session_state["last_reply_result"] = None
if "prev_reply_result" not in st.session_state:
    st.session_state["prev_reply_result"] = None
if "gemini_qa_history" not in st.session_state:
    st.session_state["gemini_qa_history"] = []
if "res_ver" not in st.session_state:
    st.session_state["res_ver"] = 0
if "refine_notes" not in st.session_state:
    st.session_state["refine_notes"] = {}


def _sync_from_selection(cat: str, sub: str, country: str, contact: str) -> None:
    info = (
        st.session_state["contacts_db"]
        .get(cat, {})
        .get(sub, {})
        .get(country, {})
        .get(contact, {})
    )
    st.session_state["salutation_val"] = info.get("salutation", "")


def on_main_cat_change() -> None:
    cat = st.session_state["sel_main_cat"]
    subs = list(st.session_state["contacts_db"].get(cat, {}).keys())
    if cat == "快遞":
        sub = "UPS" if "UPS" in subs else (subs[0] if subs else "")
        st.session_state["sel_courier_carrier"] = sub
    elif cat == "貨代":
        sub = subs[0] if subs else ""
        st.session_state["sel_forwarder_name"] = sub
    else:
        sub = subs[0] if subs else ""
        st.session_state["sel_overseas_company"] = sub

    countries = list(st.session_state["contacts_db"].get(cat, {}).get(sub, {}).keys())
    country = countries[0] if countries else ""
    st.session_state["sel_country"] = country

    contacts = list(
        st.session_state["contacts_db"].get(cat, {}).get(sub, {}).get(country, {}).keys()
    )
    contact = contacts[0] if contacts else ""
    st.session_state["sel_contact"] = contact
    _sync_from_selection(cat, sub, country, contact)


def on_sub_entity_change(sub_key: str) -> None:
    cat = st.session_state["sel_main_cat"]
    sub = st.session_state[sub_key]
    countries = list(st.session_state["contacts_db"].get(cat, {}).get(sub, {}).keys())
    country = countries[0] if countries else ""
    st.session_state["sel_country"] = country

    contacts = list(
        st.session_state["contacts_db"].get(cat, {}).get(sub, {}).get(country, {}).keys()
    )
    contact = contacts[0] if contacts else ""
    st.session_state["sel_contact"] = contact
    _sync_from_selection(cat, sub, country, contact)


def on_country_change(sub: str) -> None:
    cat = st.session_state["sel_main_cat"]
    country = st.session_state["sel_country"]
    contacts = list(
        st.session_state["contacts_db"].get(cat, {}).get(sub, {}).get(country, {}).keys()
    )
    contact = contacts[0] if contacts else ""
    st.session_state["sel_contact"] = contact
    _sync_from_selection(cat, sub, country, contact)


def on_contact_change(sub: str) -> None:
    cat = st.session_state["sel_main_cat"]
    country = st.session_state["sel_country"]
    contact = st.session_state["sel_contact"]
    _sync_from_selection(cat, sub, country, contact)


# ================= 結構化輸出與呼叫函式 =================
class EmailReplyOutput(BaseModel):
    subject: str = Field(description="建議的英文信件主旨（若有訂單編號請務必包含在主旨中）")
    standard_reply: str = Field(
        description="標準專業版英文回信草稿（包含指定稱呼、分段正文與署名 Bella, Sales Assistant | Problue；不包含內部職位備註）"
    )
    concise_reply: str = Field(
        description="簡潔俐落版英文回信草稿（適合快速跟進或熟客，同樣包含指定稱呼與署名；不包含內部職位備註）"
    )
    standard_reply_zh: str = Field(
        description="standard_reply 的繁體中文對照翻譯：忠實逐段翻譯，段落順序與英文完全一致，段與段之間空一行，包含稱呼與署名，不要加註解"
    )
    concise_reply_zh: str = Field(
        description="concise_reply 的繁體中文對照翻譯：忠實逐段翻譯，段落順序與英文完全一致，段與段之間空一行，包含稱呼與署名，不要加註解"
    )
    zh_checklist: list[str] = Field(
        description="中文重點核對清單，逐條列出本信確認的事實與防呆檢查點，方便寄出前核對"
    )


def build_system_instruction(guardrails: list[str]) -> str:
    rules_text = "\n".join(
        f"{idx}. {rule}" for idx, rule in enumerate(guardrails, start=1)
    )
    return f"""你是一位熟悉國際貿易與外貿業助實務的英文商務溝通助手，正在協助 Bella（Sales Assistant | Problue）撰寫或回覆英文商務信件。

【Bella 的寫作語氣與結構習慣】
- 親切禮貌、有條理且人情味適中，多採用公司視角（we / our），避免生硬翻譯腔。
- 若使用者有指定「信件開頭稱呼」（如 Dear Chris 或 Hi Mireya），信件開頭第一行務必完全照該稱呼開頭；若未指定，可依來信或對象使用合適的英文稱呼。
- 常用自然開場如 "Good day!"、"We hope this email finds you well." 或 "Thank you for your kind words!" / "Thank you for your prompt reply."。
- 若指示為「第一次見na～」，開頭寒暄後務必自然帶出自我介紹，例如："My name is Bella, and I will be taking over your shipping and coordination moving forward. It is a pleasure to work with you."。
- 若有提供「訂單編號」（例如 PO#12345(B2PT2610002)），請在信件主旨（Subject）與內文適當位置清楚標示該完整編號。
- 若有提供「主管建議」，請優先融入該建議的回覆方向與重點。
- 段落分工清楚：將「自我介紹」、「出貨/備貨狀態」、「物流/貨代/運費安排」、「付款/單據確認」自然串接並拆成獨立段落。
- 常用收尾句型包含："We hope you receive the goods smoothly."、"Please let me know if you need any further details."、"Please do not hesitate to contact us if you have any questions."、"We look forward to hearing from you!" 或 "Awaiting your reply."。

【嚴格遵守的固定防呆規則】
{rules_text}

【其他要求】
- 將使用者勾選的所有目地、「其他」自訂內容、主管建議與勾選的補充細節自然整合成一封通順的信件。
- zh_checklist 請用繁體中文條列本信確認的關鍵資訊與防呆確認點。
- standard_reply_zh、concise_reply_zh 是對應英文信的繁體中文逐段對照翻譯，供 Bella 檢查內容；段落順序要與英文一致，翻譯要忠實、口語自然，不要自行增減資訊。
"""


def generate_customer_reply(
    api_key: str,
    main_cat: str,
    sub_entity: str,
    country: str,
    contact_name: str,
    internal_title: str,
    contact_habit_note: str,
    salutation: str,
    order_code: str,
    is_first_meet: bool,
    selected_prompts: list[str],
    other_custom_text: str,
    supervisor_advice: str,
    selected_detail_prompts: list[str],
    extra_custom_notes: str,
    customer_email: str,
    model: str = "gemini-2.5-flash",
) -> EmailReplyOutput:
    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(api_version="v1beta"),
    )
    system_instruction = build_system_instruction(FIXED_GUARDRAILS_ZH)

    sections = []

    meta_lines = []
    if main_cat:
        target_str = f"{main_cat} / {sub_entity}"
        if country:
            target_str += f" / {country}"
        if contact_name:
            target_str += f" / {contact_name}"
        meta_lines.append(f"- 對象歸檔：{target_str}")
    if internal_title:
        meta_lines.append(f"- 聯絡人內部職位參考（勿寫入給客戶的信件）：{internal_title}")
    if contact_habit_note:
        meta_lines.append(f"- 此聯絡人過往習慣備註（供語氣與細節參考）：{contact_habit_note}")
    if salutation.strip():
        meta_lines.append(f"- 指定信件開頭稱呼：{salutation.strip()}")
    if order_code:
        meta_lines.append(f"- 訂單編號：{order_code}（請務必帶入主旨與信件內文）")
    if meta_lines:
        sections.append("【基本資訊】\n" + "\n".join(meta_lines))

    if is_first_meet:
        sections.append(
            "【⚠️ 開場設定：第一次見na～】這是 Bella 第一次與對方聯絡或新接手對接，請在信件開頭禮貌問候後先自我介紹（說明自己是 Bella，接下來將負責相關聯繫與出貨協調）。"
        )
    else:
        sections.append("【開場設定】非首次聯絡，無需重複自我介紹，直接禮貌問候並進入主題即可。")

    all_goals = list(selected_prompts)
    if other_custom_text.strip():
        all_goals.append(f"【其他自訂目地】{other_custom_text.strip()}")
    if all_goals:
        sections.append("【本次要傳達的目地】\n" + "\n".join(f"- {g}" for g in all_goals))

    if supervisor_advice.strip():
        sections.append(f"【主管建議（請務必納入回覆方向）】\n{supervisor_advice.strip()}")

    all_details = list(selected_detail_prompts)
    if extra_custom_notes.strip():
        all_details.append(f"【其他補充數字/單號/交代】{extra_custom_notes.strip()}")
    if all_details:
        sections.append("【本次補充細節 / 特殊交代】\n" + "\n".join(f"- {d}" for d in all_details))

    combined_notes = "\n\n".join(sections)

    prompt = f"""【對方來信原文（若無則為主動發信）】
{customer_email.strip() if customer_email.strip() else "（無原文，請依以下資訊主動擬信）"}

{combined_notes}
"""

    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            response_schema=EmailReplyOutput,
            temperature=0.3,
        ),
    )

    if response.parsed is None:
        raise RuntimeError("模型未能成功解析結構化回信內容，請稍後再試。")

    return response.parsed


class RefinedReply(BaseModel):
    english_reply: str = Field(
        description="依修改後中文重寫、潤飾過的完整英文信（含稱呼與署名 Bella, Sales Assistant | Problue；不含主旨）"
    )
    zh_translation: str = Field(
        description="新英文信的繁體中文逐段對照翻譯，段落順序與英文一致，段與段之間空一行"
    )
    change_notes: list[str] = Field(
        description="用繁體中文條列這次依使用者修改而改動的地方（例如：新增了哪一句、刪掉了什麼、語氣調整），最多 5 條"
    )


def refine_reply(
    api_key: str,
    english_draft: str,
    zh_original: str,
    zh_edited: str,
    subject: str,
    order_code: str,
    salutation: str,
    model: str = "gemini-2.5-flash",
) -> RefinedReply:
    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(api_version="v1beta"),
    )
    system_instruction = (
        build_system_instruction(FIXED_GUARDRAILS_ZH)
        + """
【本次任務：依 Bella 修改後的中文，重寫英文信】
- Bella 看了英文信的中文對照後，直接在中文上增刪或改寫。請比對「原中文對照」與「修改後中文」找出差異（新增、刪除、改寫）。
- 以「修改後中文」為最終要表達的內容，把差異精準反映到英文信中；沒有被改動的部分，盡量保留原英文的用字與結構。
- 新增或改寫的句子要潤飾成自然、專業、親切的英文（符合 Bella 的語氣），不要生硬直譯，也不要加入中文裡沒提到的事實、金額、日期。
- 保留指定稱呼、訂單編號與 Bella 的署名；防呆規則仍然全部適用。
- 只回傳指定欄位；english_reply 不含主旨。
"""
    )
    meta = []
    if subject:
        meta.append(f"- 目前主旨：{subject}")
    if order_code:
        meta.append(f"- 訂單編號：{order_code}")
    if salutation.strip():
        meta.append(f"- 指定信件開頭稱呼：{salutation.strip()}")
    prompt = f"""{chr(10).join(meta)}

【目前英文信】
{english_draft}

【原中文對照】
{zh_original}

【Bella 修改後的中文（以此為準）】
{zh_edited}
"""
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            response_schema=RefinedReply,
            temperature=0.3,
        ),
    )
    if response.parsed is None:
        raise RuntimeError("模型未能成功解析修改後的內容，請稍後再試。")
    return response.parsed


def render_editable_version(
    res: "EmailReplyOutput",
    kind: str,
    api_key: str,
    model: str,
    order_code: str,
    salutation: str,
) -> None:
    """英文在上、可編輯中文在下；改完中文可重新生成英文。"""
    en_field = "standard_reply" if kind == "standard" else "concise_reply"
    zh_field = f"{en_field}_zh"
    en_text = getattr(res, en_field)
    zh_text = getattr(res, zh_field, "") or ""
    ver = st.session_state["res_ver"]

    st.caption("🇺🇸 English（點右上角複製）")
    show_code(en_text)

    st.caption("🇹🇼 中文對照　可直接改字、補內容，改完按下方按鈕")
    zh_edit = st.text_area(
        "中文對照",
        value=zh_text,
        height=280,
        key=f"zh_edit_{kind}_{ver}",
        label_visibility="collapsed",
    )

    notes = st.session_state.get("refine_notes", {}).get(kind)
    if notes:
        st.success("上次修改：" + "；".join(notes))

    if st.button(
        "✨ 依中文修改，重新生成英文",
        key=f"btn_refine_{kind}_{ver}",
        use_container_width=True,
    ):
        if not api_key.strip():
            st.error("請先在左側欄輸入 Gemini API Key。")
        elif zh_edit.strip() == zh_text.strip():
            st.warning("中文內容還沒有變動，請先修改或補充再按。")
        else:
            with st.spinner("正在依你的中文修改重寫英文..."):
                try:
                    out = refine_reply(
                        api_key=api_key.strip(),
                        english_draft=en_text,
                        zh_original=zh_text,
                        zh_edited=zh_edit,
                        subject=res.subject,
                        order_code=order_code,
                        salutation=salutation,
                        model=model,
                    )
                    st.session_state["prev_reply_result"] = res
                    st.session_state["last_reply_result"] = res.model_copy(
                        update={en_field: out.english_reply, zh_field: out.zh_translation}
                    )
                    st.session_state["res_ver"] += 1
                    st.session_state["refine_notes"] = {kind: out.change_notes}
                    st.rerun()
                except Exception as exc:
                    st.error(f"重新生成失敗：{exc}")


def ask_gemini_general(api_key: str, question: str, model: str = "gemini-2.5-flash") -> str:
    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(api_version="v1beta"),
    )
    response = client.models.generate_content(
        model=model,
        contents=question.strip(),
        config=types.GenerateContentConfig(
            system_instruction="你是 Bella 的專屬 AI 顧問，熟悉國貿、物流、快遞、發票與英文商務溝通。請以親切、清晰、實用的繁體中文回答問題。",
            temperature=0.5,
        ),
    )
    return response.text or "目前沒有收到文字回覆，請再試一次。"


# ================= 側邊欄：只留設定 =================
with st.sidebar:
    st.header("⚙️ 設定")
    try:
        saved_secret_key = st.secrets.get("GEMINI_API_KEY", "")
    except Exception:
        saved_secret_key = ""

    default_api_key = saved_secret_key or os.getenv("GEMINI_API_KEY", "")

    if default_api_key:
        st.success("已自動載入預設 Gemini API Key")

    api_key_input = st.text_input(
        "Gemini API Key",
        value=default_api_key,
        type="password",
        help="已設定 .streamlit/secrets.toml 或雲端 Secrets 時會自動帶入。",
    )
    model_choice = st.selectbox(
        "模型",
        options=["gemini-2.5-flash", "gemini-2.5-pro"],
        index=0,
    )

    st.divider()
    with st.expander("🛡️ 固定防呆規則", expanded=False):
        for idx, rule in enumerate(FIXED_GUARDRAILS_ZH, start=1):
            st.markdown(f"**{idx}.** {rule}")


# ================= 主畫面標題 =================
st.title("貝拉の回信神器")
st.caption("選對象　→　勾目地　→　一鍵生成英文回信")

tab_reply, tab_ask, tab_contacts = st.tabs(["✉️ 回信生成", "💬 問問看", "👥 客戶管理"])

# =====================================================================
# 分頁一：回信生成
# =====================================================================
with tab_reply:
    col_left, col_right = st.columns([1.05, 1.2], gap="large")

    # ---------------- 左：輸入 ----------------
    with col_left:
        # ① 對象與訂單
        with st.container(border=True):
            card_title("① 選擇對象與訂單")

            main_cat = st.selectbox(
                "客戶分類",
                options=["海外", "貨代", "快遞"],
                key="sel_main_cat",
                on_change=on_main_cat_change,
            )

            sub_entity = ""
            if main_cat == "海外":
                overseas_companies = list(st.session_state["contacts_db"].get("海外", {}).keys())
                col_o1, col_o2 = st.columns(2)
                with col_o1:
                    if overseas_companies:
                        st.selectbox(
                            "已存客戶（公司名稱）",
                            options=overseas_companies,
                            key="sel_overseas_company",
                            on_change=lambda: on_sub_entity_change("sel_overseas_company"),
                        )
                    else:
                        st.caption("目前沒有已存海外客戶，請直接輸入或到「客戶管理」新增。")
                with col_o2:
                    custom_company_input = st.text_input(
                        "或輸入新客戶公司名稱",
                        placeholder="新客戶才需要填",
                    )
                sub_entity = custom_company_input.strip() or st.session_state.get(
                    "sel_overseas_company", ""
                )

            elif main_cat == "貨代":
                forwarder_list = list(st.session_state["contacts_db"].get("貨代", {}).keys())
                if forwarder_list:
                    sub_entity = st.selectbox(
                        "貨代公司",
                        options=forwarder_list,
                        key="sel_forwarder_name",
                        on_change=lambda: on_sub_entity_change("sel_forwarder_name"),
                    )
                else:
                    sub_entity = st.text_input("貨代公司名稱", placeholder="例如：Forwarder 公司名")

            else:
                courier_options = ["UPS", "FedEx", "DHL"]
                extra_couriers = [
                    k
                    for k in st.session_state["contacts_db"].get("快遞", {}).keys()
                    if k not in courier_options
                ]
                sub_entity = st.selectbox(
                    "快遞公司",
                    options=courier_options + extra_couriers,
                    key="sel_courier_carrier",
                    on_change=lambda: on_sub_entity_change("sel_courier_carrier"),
                )

            countries_map = st.session_state["contacts_db"].get(main_cat, {}).get(sub_entity, {})
            country_list = list(countries_map.keys()) if countries_map else ["未指定國家"]
            if st.session_state.get("sel_country") not in country_list:
                st.session_state["sel_country"] = country_list[0]

            contacts_map_pre = countries_map.get(st.session_state["sel_country"], {}) if countries_map else {}
            contact_list = list(contacts_map_pre.keys()) if contacts_map_pre else ["（手動輸入聯絡人）"]
            if st.session_state.get("sel_contact") not in contact_list:
                st.session_state["sel_contact"] = contact_list[0]

            c_col1, c_col2 = st.columns(2)
            with c_col1:
                selected_country = st.selectbox(
                    "國家",
                    options=country_list,
                    key="sel_country",
                    on_change=lambda: on_country_change(sub_entity),
                )

            contacts_map = countries_map.get(selected_country, {}) if countries_map else {}
            contact_list = list(contacts_map.keys()) if contacts_map else ["（手動輸入聯絡人）"]
            if st.session_state.get("sel_contact") not in contact_list:
                st.session_state["sel_contact"] = contact_list[0]

            with c_col2:
                selected_contact = st.selectbox(
                    "聯絡人",
                    options=contact_list,
                    key="sel_contact",
                    on_change=lambda: on_contact_change(sub_entity),
                )

            if not st.session_state["salutation_val"] and selected_contact != "（手動輸入聯絡人）":
                _sync_from_selection(main_cat, sub_entity, selected_country, selected_contact)

            contact_info = contacts_map.get(selected_contact, {})
            internal_title_val = contact_info.get("internal_title", "")
            contact_habit_note = contact_info.get("default_notes", "")

            if internal_title_val or contact_habit_note:
                info_parts = []
                if internal_title_val:
                    info_parts.append(f"職位／備註：{internal_title_val}")
                if contact_habit_note:
                    info_parts.append(f"過往習慣：{contact_habit_note}")
                st.caption("🔒 僅內部參考，不會寫進信件　｜　" + "　｜　".join(info_parts))

            salutation_input = st.text_input(
                "信件開頭稱呼",
                key="salutation_val",
                placeholder="例如：Dear Chris 或 Hi Mireya",
            )

            po_col1, po_col2 = st.columns(2)
            with po_col1:
                po_input = st.text_input(
                    "PO#",
                    placeholder="客戶的編號，例如 12345",
                    help="選填；會自動補上 PO# 前綴。",
                )
            with po_col2:
                b2pt_input = st.text_input(
                    "B2PT",
                    placeholder="我們家的編號，例如 2610002",
                    help="選填；會自動補上 B2PT 前綴。",
                )

            combined_order_code = format_order_code(po_input, b2pt_input)
            if combined_order_code:
                st.caption(f"📌 組合單號：`{combined_order_code}`")

        # ② 本次要寫什麼
        with st.container(border=True):
            card_title("② 本次要寫什麼")

            is_first_meet = st.checkbox("👋 第一次見na～（信中會自我介紹）", value=False)

            selected_prompts = multi_pick("目地（可複選）", ACTION_MODULES, key="pick_goals")

            is_other_goal = st.checkbox("✏️ 其他目地（自己輸入）", key="chk_other_goal")
            other_custom_text = ""
            if is_other_goal:
                other_custom_text = st.text_area(
                    "其他目地說明",
                    height=75,
                    placeholder="輸入你這次想讓系統幫你寫出來的特定內容或需求...",
                    label_visibility="collapsed",
                )

            selected_detail_prompts = multi_pick(
                "補充細節（常用備註，用勾的就好）", COMMON_DETAIL_MODULES, key="pick_details"
            )

            is_other_detail = st.checkbox("➕ 其他補充（金額、單號、臨時交代）", key="chk_other_detail")
            extra_custom_notes = ""
            if is_other_detail:
                extra_custom_notes = st.text_area(
                    "其他補充細節",
                    height=80,
                    placeholder="例如：UPS 運費 US$315 / FedEx US$290；Tracking# 1Z999AA10123456784",
                    label_visibility="collapsed",
                )

        # ③ 選填
        with st.container(border=True):
            card_title("③ 選填資料")
            supervisor_advice = st.text_area(
                "主管建議",
                height=80,
                placeholder="例如：先請客人確認數量與寄送方式，運費等確認後再報，不要先承諾交期。",
                help="主管有交代怎麼回時填在這裡，會優先納入回覆方向。",
            )
            customer_email_input = st.text_area(
                "對方來信原文",
                height=110,
                placeholder="回信時貼上對方來信；主動發信可留空。",
            )

    # ---------------- 右：按鈕 + 結果 ----------------
    with col_right:
        generate_btn = st.button("🚀 生成英文回信草稿", type="primary", use_container_width=True)

        if generate_btn:
            if not api_key_input.strip():
                st.error("請先在左側欄輸入 Gemini API Key。")
            elif (
                not is_first_meet
                and not selected_prompts
                and not other_custom_text.strip()
                and not selected_detail_prompts
                and not extra_custom_notes.strip()
                and not supervisor_advice.strip()
                and not customer_email_input.strip()
            ):
                st.warning("請至少勾選一個目地或補充細節，或填寫主管建議／來信原文。")
            else:
                with st.spinner("正在整合勾選項目與主管建議生成英文回信..."):
                    try:
                        new_res = generate_customer_reply(
                            api_key=api_key_input.strip(),
                            main_cat=main_cat,
                            sub_entity=sub_entity,
                            country=selected_country,
                            contact_name=selected_contact,
                            internal_title=internal_title_val,
                            contact_habit_note=contact_habit_note,
                            salutation=salutation_input,
                            order_code=combined_order_code,
                            is_first_meet=is_first_meet,
                            selected_prompts=selected_prompts,
                            other_custom_text=other_custom_text,
                            supervisor_advice=supervisor_advice,
                            selected_detail_prompts=selected_detail_prompts,
                            extra_custom_notes=extra_custom_notes,
                            customer_email=customer_email_input,
                            model=model_choice,
                        )
                        if st.session_state["last_reply_result"] is not None:
                            st.session_state["prev_reply_result"] = st.session_state["last_reply_result"]
                        st.session_state["last_reply_result"] = new_res
                        st.session_state["res_ver"] += 1
                        st.session_state["refine_notes"] = {}
                    except Exception as exc:
                        st.error(f"生成失敗：{exc}")

        current_res: EmailReplyOutput | None = st.session_state.get("last_reply_result")
        prev_res: EmailReplyOutput | None = st.session_state.get("prev_reply_result")

        if current_res is None:
            with st.container(border=True):
                st.markdown("**還沒有草稿**")
                st.caption("選好對象、勾選目地後，按上方「生成英文回信草稿」。結果會出現在這裡，點程式碼框右上角即可複製。")
        else:
            with st.container(border=True):
                st.markdown("**📌 主旨**")
                show_code(current_res.subject)

                t_std, t_short, t_prev = st.tabs(["標準專業版", "簡潔版", "上一次"])
                with t_std:
                    render_editable_version(
                        current_res, "standard", api_key_input, model_choice,
                        combined_order_code, salutation_input,
                    )
                with t_short:
                    render_editable_version(
                        current_res, "concise", api_key_input, model_choice,
                        combined_order_code, salutation_input,
                    )
                with t_prev:
                    if prev_res is not None:
                        st.caption("上一次的主旨")
                        show_code(prev_res.subject)
                        st.caption("標準專業版")
                        show_code(prev_res.standard_reply)
                        st.caption("簡潔版")
                        show_code(prev_res.concise_reply)
                    else:
                        st.caption("再生成一次後，前一次的草稿會保留在這裡。")

            with st.container(border=True):
                st.markdown("**✅ 寄出前核對**")
                for idx, item in enumerate(current_res.zh_checklist, start=1):
                    st.markdown(f"{idx}. {item}")

# =====================================================================
# 分頁二：問問看
# =====================================================================
with tab_ask:
    st.caption("外貿英文怎麼寫、單據或快遞怎麼處理，或任何想問的問題，直接輸入就能問。")

    if st.session_state["gemini_qa_history"]:
        if st.button("清除對話紀錄", key="btn_clear_chat"):
            st.session_state["gemini_qa_history"] = []
            st.rerun()

    for chat_item in st.session_state["gemini_qa_history"]:
        with st.chat_message("user"):
            st.markdown(chat_item["q"])
        with st.chat_message("assistant"):
            st.markdown(chat_item["a"])

    ask_q = st.chat_input("例如：這封信如果客人問關稅怎麼回比較客氣？")
    if ask_q and ask_q.strip():
        if not api_key_input.strip():
            st.error("請先在左側欄輸入 Gemini API Key。")
        else:
            with st.spinner("正在思考並回覆你的問題..."):
                try:
                    ans = ask_gemini_general(
                        api_key=api_key_input.strip(),
                        question=ask_q.strip(),
                        model=model_choice,
                    )
                    st.session_state["gemini_qa_history"].append({"q": ask_q.strip(), "a": ans})
                    st.rerun()
                except Exception as exc:
                    st.error(f"提問失敗：{exc}")

# =====================================================================
# 分頁三：客戶管理
# =====================================================================
with tab_contacts:
    mg_left, mg_right = st.columns(2, gap="large")

    # ---------------- 新增 ----------------
    with mg_left:
        with st.container(border=True):
            card_title("➕ 新增客戶 / 聯絡人")
            save_cat = st.selectbox(
                "客戶分類", options=["海外", "貨代", "快遞"], key="save_cat"
            )
            if save_cat == "海外":
                save_sub = st.text_input("客戶公司名稱", placeholder="例如：ABC Diving Corp.", key="save_sub_overseas")
            elif save_cat == "貨代":
                save_sub = st.text_input("貨代公司名稱", placeholder="例如：Forwarder 公司名", key="save_sub_forwarder")
            else:
                save_sub = st.selectbox("快遞公司", options=["UPS", "FedEx", "DHL"], key="save_sub_courier")

            n1, n2 = st.columns(2)
            with n1:
                save_country = st.text_input("國家 / 地區", placeholder="例如：西班牙、美國", key="save_country")
            with n2:
                save_contact = st.text_input("聯絡人姓名", placeholder="例如：Elena", key="save_contact")
            save_salutation = st.text_input("信件開頭稱呼", placeholder="例如：Hi Elena", key="save_salutation")
            save_internal_title = st.text_input(
                "職位 / 內部備註",
                placeholder="例如：財務窗口 / 採購經理",
                help="只給你看，不會寫進信件。",
                key="save_internal_title",
            )
            save_default_notes = st.text_area(
                "客戶習慣備註",
                height=70,
                placeholder="例如：習慣刷卡支付運費、只開 Invoice。",
                key="save_default_notes",
            )

            if st.button("💾 儲存並歸檔", use_container_width=True, type="primary", key="btn_save_new"):
                c_val = save_cat.strip()
                s_val = save_sub.strip()
                ct_val = save_country.strip() or "未指定國家"
                p_val = save_contact.strip()
                if c_val and s_val and p_val:
                    st.session_state["contacts_db"].setdefault(c_val, {}).setdefault(s_val, {}).setdefault(ct_val, {})[p_val] = {
                        "salutation": save_salutation.strip() or f"Hi {p_val}",
                        "internal_title": save_internal_title.strip(),
                        "default_notes": save_default_notes.strip(),
                    }
                    st.success(f"已歸檔：{c_val} ＞ {s_val} ＞ {ct_val} ＞ {p_val}")
                    st.rerun()
                else:
                    st.warning("請至少填寫「公司名稱」與「聯絡人姓名」。")

    # ---------------- 編輯 / 刪除 ----------------
    with mg_right:
        with st.container(border=True):
            card_title("✏️ 編輯 / 刪除已存資料")
            edit_cat = st.selectbox("分類", options=["海外", "貨代", "快遞"], key="edit_cat")
            subs_in_cat = list(st.session_state["contacts_db"].get(edit_cat, {}).keys())

            if not subs_in_cat:
                st.caption("此分類目前沒有已存資料。")
            else:
                edit_sub = st.selectbox("公司 / 對象", options=subs_in_cat, key="edit_sub")

                new_company_name = st.text_input(
                    "公司 / 對象名稱",
                    value=edit_sub,
                    key=f"rename_sub_{edit_cat}_{edit_sub}",
                )
                btn_col1, btn_col2 = st.columns(2)
                with btn_col1:
                    if st.button("更新公司名稱", use_container_width=True, key="btn_rename_sub"):
                        clean_new = new_company_name.strip()
                        if clean_new and clean_new != edit_sub:
                            cat_dict = st.session_state["contacts_db"][edit_cat]
                            if clean_new in cat_dict:
                                for ct_k, ppl_v in cat_dict[edit_sub].items():
                                    cat_dict[clean_new].setdefault(ct_k, {}).update(ppl_v)
                            else:
                                cat_dict[clean_new] = cat_dict[edit_sub]
                            del cat_dict[edit_sub]
                            st.success(f"已改名為：{clean_new}")
                            st.rerun()
                with btn_col2:
                    if st.button("🗑️ 刪除整間公司", use_container_width=True, key="btn_del_sub"):
                        del st.session_state["contacts_db"][edit_cat][edit_sub]
                        st.success(f"已刪除：{edit_sub}")
                        st.rerun()

                st.divider()
                countries_in_sub = list(
                    st.session_state["contacts_db"].get(edit_cat, {}).get(edit_sub, {}).keys()
                )
                if countries_in_sub:
                    e1, e2 = st.columns(2)
                    with e1:
                        edit_country = st.selectbox("國家", options=countries_in_sub, key="edit_country")
                    people_in_country = list(
                        st.session_state["contacts_db"][edit_cat][edit_sub].get(edit_country, {}).keys()
                    )
                    if people_in_country:
                        with e2:
                            edit_person = st.selectbox("聯絡人", options=people_in_country, key="edit_person")
                        cur_info = st.session_state["contacts_db"][edit_cat][edit_sub][edit_country][edit_person]
                        k = f"{edit_cat}_{edit_sub}_{edit_country}_{edit_person}"

                        u1, u2 = st.columns(2)
                        with u1:
                            upd_country = st.text_input("國家 / 地區", value=edit_country, key=f"upd_ct_{k}")
                        with u2:
                            upd_person = st.text_input("聯絡人姓名", value=edit_person, key=f"upd_p_{k}")
                        upd_salutation = st.text_input(
                            "信件開頭稱呼", value=cur_info.get("salutation", ""), key=f"upd_sal_{k}"
                        )
                        upd_internal = st.text_input(
                            "職位 / 內部備註（只給你看）",
                            value=cur_info.get("internal_title", ""),
                            key=f"upd_int_{k}",
                        )
                        upd_notes = st.text_area(
                            "客戶習慣備註",
                            value=cur_info.get("default_notes", ""),
                            height=70,
                            key=f"upd_note_{k}",
                        )

                        p_btn1, p_btn2 = st.columns(2)
                        with p_btn1:
                            if st.button("💾 儲存修改", use_container_width=True, type="primary", key="btn_save_person_edit"):
                                target_ct = upd_country.strip() or edit_country
                                target_p = upd_person.strip() or edit_person
                                sub_dict = st.session_state["contacts_db"][edit_cat][edit_sub]

                                del sub_dict[edit_country][edit_person]
                                if not sub_dict[edit_country]:
                                    del sub_dict[edit_country]

                                sub_dict.setdefault(target_ct, {})[target_p] = {
                                    "salutation": upd_salutation.strip() or f"Hi {target_p}",
                                    "internal_title": upd_internal.strip(),
                                    "default_notes": upd_notes.strip(),
                                }
                                st.success(f"已更新聯絡人：{target_p}")
                                st.rerun()
                        with p_btn2:
                            if st.button("🗑️ 刪除聯絡人", use_container_width=True, key="btn_del_person"):
                                sub_dict = st.session_state["contacts_db"][edit_cat][edit_sub]
                                del sub_dict[edit_country][edit_person]
                                if not sub_dict[edit_country]:
                                    del sub_dict[edit_country]
                                st.success(f"已刪除聯絡人：{edit_person}")
                                st.rerun()

    # ---------------- 匯出 ----------------
    with st.expander("📤 匯出目前客戶名單（貼回 GitHub 永久保存）", expanded=False):
        st.caption(
            "在網頁上新增或修改客戶後，複製下方內容，到 GitHub 編輯 app.py，取代原本的 DEFAULT_CONTACTS_DB 並 Commit，重開就不會消失。"
        )
        formatted_db = pprint.pformat(st.session_state["contacts_db"], indent=4, sort_dicts=False)
        show_code(f"DEFAULT_CONTACTS_DB = {formatted_db}")

    page_icon="✉️",
    layout="wide",
)
def apply_custom_theme() -> None:
    st.markdown(
        """
        <style>
        .stApp {
            background-color: #FAF6F0;
            color: #2C2621;
        }
        [data-testid="stSidebar"] {
            background-color: #F3ECE1;
            border-right: 1px solid #E2D6C5;
        }
        .stButton > button[kind="primary"] {
            background-color: #C87D4B;
            color: #FFFFFF;
            border: none;
            border-radius: 10px;
            padding: 0.6rem 1.2rem;
            font-weight: 600;
        }
        .stButton > button[kind="primary"]:hover {
            background-color: #B26A3B;
        }
        .stButton > button:not([kind="primary"]) {
            border-radius: 10px;
            border: 1px solid #D8C7B2;
            background-color: #FFFDF9;
            color: #2C2621;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


apply_custom_theme()
FIXED_GUARDRAILS_ZH = [
    "訂單若已準備好，只寫 ready（訂單已備妥），絕對不要自行加上 ahead of schedule、early 或提早完成。",
    "運費若是 Bella 幫忙查詢提供的，清楚說明運費由我方協助查詢提供，待確認寄送方式後提供明細或選項。",
    "單據名稱嚴格依指令或重點指定：若只提到 Invoice，就只寫 Invoice，不要自行加上 Commercial Invoice。",
    "所有事實皆以勾選項目、主管建議與補充說明為準，不自行腦補交期、折扣、庫存量或付款條件。",
    "聯絡人的「內部職位／備註」僅供 Bella 內部辨識與參考，絕對不要寫進寄給客戶或廠商的英文信件內文。",
    "英文回信結尾統一以 Bella（Sales Assistant | Problue）署名；若涉及公司基本資料，使用 PROBLUE INTERNATIONAL CORP.、NO. 32-28, LN. 1, SEC. 2, MINZU RD., TANZI DIST., TAICHUNG 427, TAIWAN、TEL: 04-25689717。",
]

# 結構：CONTACTS_DB[客戶分類][客戶公司名稱 / 貨代 / 快遞][國家][聯絡人姓名]
DEFAULT_CONTACTS_DB: dict[str, dict[str, dict[str, dict[str, dict[str, str]]]]] = {
    "海外": {
        "Casco": {
            "西班牙": {
                "Mireya": {
                    "salutation": "Hi Mireya",
                    "internal_title": "西班牙主要採購與帳務對接窗口",
                    "default_notes": "長線合作客戶；分項訂單與未付餘額需列明細表核對，付款後請附匯款水單。",
                },
                "Carlos": {
                    "salutation": "Hi Carlos",
                    "internal_title": "西班牙倉庫 / 收貨窗口",
                    "default_notes": "主要對接收貨與箱單確認。",
                },
            }
        },
        "Luke Marine Supply": {
            "美國": {
                "Luke": {
                    "salutation": "Dear Luke",
                    "internal_title": "美國採購窗口 / 習慣信用卡付款",
                    "default_notes": "付款習慣簽回 Credit Card Authorization Form；海關申報發票比照先前需求以每件 USD 2.00 申報。",
                }
            }
        },
        "Chris Diving Co.": {
            "美國": {
                "Chris": {
                    "salutation": "Dear Chris",
                    "internal_title": "美國客戶窗口 / 運費多刷卡",
                    "default_notes": "運費多建議對方使用信用卡並簽回 Credit Card Authorization Form。",
                }
            }
        },
        "Jay Ocean Gear": {
            "美國": {
                "Jay": {
                    "salutation": "Hi Jay",
                    "internal_title": "美國詢價窗口",
                    "default_notes": "需比較不同快遞運費與預估天數供挑選。",
                }
            }
        },
    },
    "貨代": {
        "Joel Parnes Logistics": {
            "台灣 / 國際": {
                "Joel Parnes": {
                    "salutation": "Hi Joel Parnes",
                    "internal_title": "主要貨代窗口（Forwarder）",
                    "default_notes": "需附 Invoice 與 Packing List，並提供 Problue 完整公司地址與電話。",
                }
            }
        }
    },
    "快遞": {
        "UPS": {
            "台灣 / 全球": {
                "UPS 客服 / 取件窗口": {
                    "salutation": "Hi UPS Team",
                    "internal_title": "快遞公司 - UPS",
                    "default_notes": "確認取件時間、追蹤單號或運費報價。",
                }
            }
        },
        "FedEx": {
            "台灣 / 全球": {
                "FedEx 客服 / 取件窗口": {
                    "salutation": "Hi FedEx Team",
                    "internal_title": "快遞公司 - FedEx",
                    "default_notes": "確認取件時間、追蹤單號或運費報價。",
                }
            }
        },
        "DHL": {
            "台灣 / 全球": {
                "DHL 客服 / 取件窗口": {
                    "salutation": "Hi DHL Team",
                    "internal_title": "快遞公司 - DHL",
                    "default_notes": "確認取件時間、追蹤單號或運費報價。",
                }
            }
        },
    },
}

ACTION_MODULES = [
    {
        "id": "goods_ready",
        "label": "📦 貨物已準備好（Ready）",
        "prompt_zh": "通知對方貨物已經準備好了（只寫 ready，不要寫提早完成）。",
    },
    {
        "id": "ask_payment",
        "label": "💰 請對方付款 / 匯款",
        "prompt_zh": "請對方安排支付款項或尾款。",
    },
    {
        "id": "confirm_payment",
        "label": "✅ 確認已收到款項",
        "prompt_zh": "感謝對方迅速安排付款，向對方確認我方已收到款項。",
    },
    {
        "id": "cc_auth_form",
        "label": "💳 請簽回信用卡授權書",
        "prompt_zh": "附上載有先前提供之信用卡資訊的 Credit Card Authorization Form，請對方確認細節、簽名並回傳以便扣款與安排出貨。",
    },
    {
        "id": "courier_quote",
        "label": "🚚 提供快遞運費選項",
        "prompt_zh": "列出各快遞選項的預估天數與費用供挑選（註明實際送達時間視當地情況而定）。",
    },
    {
        "id": "shipped_tracking",
        "label": "✈️ 通知貨已寄出 / 已取件",
        "prompt_zh": "通知對方貨物已寄出／快遞已完成取件，並祝對方順利收到貨物。",
    },
    {
        "id": "invoice_only",
        "label": "📄 確認後只開 Invoice",
        "prompt_zh": "說明確認後我方會開立 Invoice（只寫 Invoice，不要寫 Commercial Invoice）。",
    },
    {
        "id": "contact_forwarder",
        "label": "🏭 貨代提貨＋附公司資料",
        "prompt_zh": "通知貨物已備妥並附上單據，提供 Problue 完整公司英文地址與電話，請提早提供空運或取件細節。",
    },
]

COMMON_DETAIL_MODULES = [
    {
        "id": "det_freight_checked_by_us",
        "label": "🔍 運費是我幫她查的",
        "prompt_zh": "清楚說明此運費報價是由我方協助查詢整理的。",
    },
    {
        "id": "det_wire_slip",
        "label": "🧾 請提供匯款水單（bank wire slip）",
        "prompt_zh": "請對方於完成匯款後提供匯款水單（bank wire slip）以便我方財務核對。",
    },
    {
        "id": "det_cc_faster_ship",
        "label": "⚡ 建議刷卡支付以便盡快出貨",
        "prompt_zh": "建議對方可使用信用卡支付並簽回授權書，以便我方能更快速安排出貨。",
    },
    {
        "id": "det_quote_valid_1wk",
        "label": "⏳ 運費報價有效期一週",
        "prompt_zh": "備註以上運費報價有效期為一週（valid for one week）。",
    },
    {
        "id": "det_usd2_customs",
        "label": "🏷️ 海關申報每件 USD 2.00",
        "prompt_zh": "海關申報發票比照先前需求以每件 USD 2.00（USD 2.00 per piece）申報。",
    },
    {
        "id": "det_goods_paid_freight_due",
        "label": "💵 貨款已收到，僅剩運費未付",
        "prompt_zh": "說明貨款部分我方已收到，目前僅剩運費金額待支付。",
    },
    {
        "id": "det_tracking_attached",
        "label": "🔢 追蹤單號（Tracking Number）如補充欄",
        "prompt_zh": "在信中清楚附上本次提供的快遞追蹤單號（Tracking Number）供查詢。",
    },
    {
        "id": "det_attach_inv_pl",
        "label": "📎 已隨信附上 Invoice & Packing List",
        "prompt_zh": "說明已隨信附上 Invoice 與 Packing List 供核對與安排。",
    },
]


def _deep_copy_db(db: dict) -> dict:
    return {
        cat: {
            sub: {
                country: {person: info.copy() for person, info in people.items()}
                for country, people in countries.items()
            }
            for sub, countries in subs.items()
        }
        for cat, subs in db.items()
    }


def format_order_code(po_raw: str, b2pt_raw: str) -> str:
    po = po_raw.strip()
    b2pt = b2pt_raw.strip()

    if po and not po.upper().startswith("PO#"):
        po_formatted = f"PO#{po}"
    else:
        po_formatted = po

    if b2pt and not b2pt.upper().startswith("B2PT"):
        b2pt_formatted = f"B2PT{b2pt}"
    else:
        b2pt_formatted = b2pt

    if po_formatted and b2pt_formatted:
        return f"{po_formatted}({b2pt_formatted})"
    if po_formatted:
        return po_formatted
    if b2pt_formatted:
        return b2pt_formatted
    return ""


# ================= 初始化 Session State =================
if "contacts_db" not in st.session_state:
    st.session_state["contacts_db"] = _deep_copy_db(DEFAULT_CONTACTS_DB)
if "salutation_val" not in st.session_state:
    st.session_state["salutation_val"] = ""
if "last_reply_result" not in st.session_state:
    st.session_state["last_reply_result"] = None
if "prev_reply_result" not in st.session_state:
    st.session_state["prev_reply_result"] = None
if "gemini_qa_history" not in st.session_state:
    st.session_state["gemini_qa_history"] = []


def _sync_from_selection(cat: str, sub: str, country: str, contact: str) -> None:
    info = (
        st.session_state["contacts_db"]
        .get(cat, {})
        .get(sub, {})
        .get(country, {})
        .get(contact, {})
    )
    st.session_state["salutation_val"] = info.get("salutation", "")


def on_main_cat_change() -> None:
    cat = st.session_state["sel_main_cat"]
    if cat == "快遞":
        subs = list(st.session_state["contacts_db"].get("快遞", {}).keys())
        default_sub = "UPS" if "UPS" in subs else (subs[0] if subs else "")
        st.session_state["sel_courier_carrier"] = default_sub
        sub = default_sub
    else:
        subs = list(st.session_state["contacts_db"].get(cat, {}).keys())
        sub = subs[0] if subs else ""
        st.session_state["sel_overseas_company"] = sub
        st.session_state["sel_forwarder_name"] = sub

    countries = list(st.session_state["contacts_db"].get(cat, {}).get(sub, {}).keys())
    country = countries[0] if countries else ""
    st.session_state["sel_country"] = country

    contacts = list(
        st.session_state["contacts_db"].get(cat, {}).get(sub, {}).get(country, {}).keys()
    )
    contact = contacts[0] if contacts else ""
    st.session_state["sel_contact"] = contact
    _sync_from_selection(cat, sub, country, contact)


def on_sub_entity_change(sub_key: str) -> None:
    cat = st.session_state["sel_main_cat"]
    sub = st.session_state[sub_key]
    countries = list(st.session_state["contacts_db"].get(cat, {}).get(sub, {}).keys())
    country = countries[0] if countries else ""
    st.session_state["sel_country"] = country

    contacts = list(
        st.session_state["contacts_db"].get(cat, {}).get(sub, {}).get(country, {}).keys()
    )
    contact = contacts[0] if contacts else ""
    st.session_state["sel_contact"] = contact
    _sync_from_selection(cat, sub, country, contact)


def on_country_change(sub: str) -> None:
    cat = st.session_state["sel_main_cat"]
    country = st.session_state["sel_country"]
    contacts = list(
        st.session_state["contacts_db"].get(cat, {}).get(sub, {}).get(country, {}).keys()
    )
    contact = contacts[0] if contacts else ""
    st.session_state["sel_contact"] = contact
    _sync_from_selection(cat, sub, country, contact)


def on_contact_change(sub: str) -> None:
    cat = st.session_state["sel_main_cat"]
    country = st.session_state["sel_country"]
    contact = st.session_state["sel_contact"]
    _sync_from_selection(cat, sub, country, contact)


# ================= 結構化輸出與呼叫函式 =================
class EmailReplyOutput(BaseModel):
    subject: str = Field(description="建議的英文信件主旨（若有訂單編號請務必包含在主旨中）")
    standard_reply: str = Field(
        description="標準專業版英文回信草稿（包含指定稱呼、分段正文與署名 Bella, Sales Assistant | Problue；不包含內部職位備註）"
    )
    concise_reply: str = Field(
        description="簡潔俐落版英文回信草稿（適合快速跟進或熟客，同樣包含指定稱呼與署名；不包含內部職位備註）"
    )
    zh_checklist: list[str] = Field(
        description="中文重點核對清單，逐條列出本信確認的事實與防呆檢查點，方便寄出前核對"
    )


def build_system_instruction(guardrails: list[str]) -> str:
    rules_text = "\n".join(
        f"{idx}. {rule}" for idx, rule in enumerate(guardrails, start=1)
    )
    return f"""你是一位熟悉國際貿易與外貿業助實務的英文商務溝通助手，正在協助 Bella（Sales Assistant | Problue）撰寫或回覆英文商務信件。

【Bella 的寫作語氣與結構習慣】
- 親切禮貌、有條理且人情味適中，多採用公司視角（we / our），避免生硬翻譯腔。
- 若使用者有指定「信件開頭稱呼」（如 Dear Chris 或 Hi Mireya），信件開頭第一行務必完全照該稱呼開頭；若未指定，可依來信或對象使用合適的英文稱呼。
- 常用自然開場如 "Good day!"、"We hope this email finds you well." 或 "Thank you for your kind words!" / "Thank you for your prompt reply."。
- 若指示為「第一次見na～」，開頭寒暄後務必自然帶出自我介紹，例如："My name is Bella, and I will be taking over your shipping and coordination moving forward. It is a pleasure to work with you."。
- 若有提供「訂單編號」（例如 PO#12345(B2PT2610002)），請在信件主旨（Subject）與內文適當位置清楚標示該完整編號。
- 若有提供「主管建議」，請優先融入該建議的回覆方向與重點。
- 段落分工清楚：將「自我介紹」、「出貨/備貨狀態」、「物流/貨代/運費安排」、「付款/單據確認」自然串接並拆成獨立段落。
- 常用收尾句型包含："We hope you receive the goods smoothly."、"Please let me know if you need any further details."、"Please do not hesitate to contact us if you have any questions."、"We look forward to hearing from you!" 或 "Awaiting your reply."。

【嚴格遵守的固定防呆規則】
{rules_text}

【其他要求】
- 將使用者勾選的所有目地、「其他」自訂內容、主管建議與勾選的補充細節自然整合成一封通順的信件。
- zh_checklist 請用繁體中文條列本信確認的關鍵資訊與防呆確認點。
"""


def generate_customer_reply(
    api_key: str,
    main_cat: str,
    sub_entity: str,
    country: str,
    contact_name: str,
    internal_title: str,
    contact_habit_note: str,
    salutation: str,
    order_code: str,
    is_first_meet: bool,
    selected_prompts: list[str],
    other_custom_text: str,
    supervisor_advice: str,
    selected_detail_prompts: list[str],
    extra_custom_notes: str,
    customer_email: str,
    model: str = "gemini-2.5-flash",
) -> EmailReplyOutput:
    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(api_version="v1beta"),
    )
    system_instruction = build_system_instruction(FIXED_GUARDRAILS_ZH)

    sections = []

    meta_lines = []
    if main_cat:
        target_str = f"{main_cat} / {sub_entity}"
        if country:
            target_str += f" / {country}"
        if contact_name:
            target_str += f" / {contact_name}"
        meta_lines.append(f"- 對象歸檔：{target_str}")
    if internal_title:
        meta_lines.append(f"- 聯絡人內部職位參考（勿寫入給客戶的信件）：{internal_title}")
    if contact_habit_note:
        meta_lines.append(f"- 此聯絡人過往習慣備註（供語氣與細節參考）：{contact_habit_note}")
    if salutation.strip():
        meta_lines.append(f"- 指定信件開頭稱呼：{salutation.strip()}")
    if order_code:
        meta_lines.append(f"- 訂單編號：{order_code}（請務必帶入主旨與信件內文）")
    if meta_lines:
        sections.append("【基本資訊】\n" + "\n".join(meta_lines))

    if is_first_meet:
        sections.append(
            "【⚠️ 開場設定：第一次見na～】這是 Bella 第一次與對方聯絡或新接手對接，請在信件開頭禮貌問候後先自我介紹（說明自己是 Bella，接下來將負責相關聯繫與出貨協調）。"
        )
    else:
        sections.append("【開場設定】非首次聯絡，無需重複自我介紹，直接禮貌問候並進入主題即可。")

    all_goals = list(selected_prompts)
    if other_custom_text.strip():
        all_goals.append(f"【其他自訂目地】{other_custom_text.strip()}")
    if all_goals:
        sections.append("【本次要傳達的目地】\n" + "\n".join(f"- {g}" for g in all_goals))

    if supervisor_advice.strip():
        sections.append(f"【主管建議（請務必納入回覆方向）】\n{supervisor_advice.strip()}")

    all_details = list(selected_detail_prompts)
    if extra_custom_notes.strip():
        all_details.append(f"【其他補充數字/單號/交代】{extra_custom_notes.strip()}")
    if all_details:
        sections.append("【本次補充細節 / 特殊交代】\n" + "\n".join(f"- {d}" for d in all_details))

    combined_notes = "\n\n".join(sections)

    prompt = f"""【對方來信原文（若無則為主動發信）】
{customer_email.strip() if customer_email.strip() else "（無原文，請依以下資訊主動擬信）"}

{combined_notes}
"""

    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            response_schema=EmailReplyOutput,
            temperature=0.3,
        ),
    )

    if response.parsed is None:
        raise RuntimeError("模型未能成功解析結構化回信內容，請稍後再試。")

    return response.parsed


def ask_gemini_general(api_key: str, question: str, model: str = "gemini-2.5-flash") -> str:
    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(api_version="v1beta"),
    )
    response = client.models.generate_content(
        model=model,
        contents=question.strip(),
        config=types.GenerateContentConfig(
            system_instruction="你是 Bella 的專屬 AI 顧問，熟悉國貿、物流、快遞、發票與英文商務溝通。請以親切、清晰、實用的繁體中文回答問題。",
            temperature=0.5,
        ),
    )
    return response.text or "目前沒有收到文字回覆，請再試一次。"


# ================= 側邊欄：API 金鑰與新增／編輯／刪除客戶 =================
with st.sidebar:
    st.header("⚙️ 系統與客戶管理")
    try:
        saved_secret_key = st.secrets.get("GEMINI_API_KEY", "")
    except Exception:
        saved_secret_key = ""

    default_api_key = saved_secret_key or os.getenv("GEMINI_API_KEY", "")

    if default_api_key:
        st.success("✅ 已自動載入預設 Gemini API Key（免重貼）")

    api_key_input = st.text_input(
        "Gemini API Key",
        value=default_api_key,
        type="password",
        help="已設定 .streamlit/secrets.toml 或雲端 Secrets 時會自動帶入。",
    )
    model_choice = st.selectbox(
        "選擇模型",
        options=["gemini-2.5-flash", "gemini-2.5-pro"],
        index=0,
    )

    st.divider()

    # 1. 新增客戶 / 聯絡人
    with st.expander("➕ 新增客戶 / 聯絡人（自動歸檔）", expanded=False):
        save_cat = st.selectbox(
            "1. 歸檔到客戶分類",
            options=["海外", "貨代", "快遞"],
            key="save_cat",
        )
        if save_cat == "海外":
            save_sub = st.text_input("2. 客戶公司名稱", placeholder="例如：ABC Diving Corp.", key="save_sub_overseas")
        elif save_cat == "貨代":
            save_sub = st.text_input("2. 貨代公司名稱", placeholder="例如：Forwarder 公司名", key="save_sub_forwarder")
        else:
            save_sub = st.selectbox("2. 快遞公司", options=["UPS", "FedEx", "DHL"], key="save_sub_courier")

        save_country = st.text_input("3. 國家 / 地區", placeholder="例如：西班牙、美國、台灣 / 全球", key="save_country")
        save_contact = st.text_input("4. 聯絡人姓名", placeholder="例如：Elena", key="save_contact")
        save_salutation = st.text_input("5. 信件開頭稱呼", placeholder="例如：Hi Elena", key="save_salutation")
        save_internal_title = st.text_input(
            "6. 職位 / 內部備註（只給你看）",
            placeholder="例如：財務窗口 / 採購經理",
            key="save_internal_title",
        )
        save_default_notes = st.text_area(
            "7. 客戶習慣備註",
            height=60,
            placeholder="例如：習慣刷卡支付運費、只開 Invoice。",
            key="save_default_notes",
        )

        if st.button("💾 儲存並自動歸檔", use_container_width=True):
            c_val = save_cat.strip()
            s_val = save_sub.strip()
            ct_val = save_country.strip() or "未指定國家"
            p_val = save_contact.strip()
            if c_val and s_val and p_val:
                st.session_state["contacts_db"].setdefault(c_val, {}).setdefault(s_val, {}).setdefault(ct_val, {})[p_val] = {
                    "salutation": save_salutation.strip() or f"Hi {p_val}",
                    "internal_title": save_internal_title.strip(),
                    "default_notes": save_default_notes.strip(),
                }
                st.success(f"已歸檔：{c_val} ＞ {s_val} ＞ {ct_val} ＞ {p_val}")
                st.rerun()
            else:
                st.warning("請至少填寫「公司名稱」與「聯絡人姓名」。")

    # 2. 編輯 / 刪除已存海外客戶、貨代、快遞與聯絡人
    with st.expander("✏️ 編輯 / 刪除已存客戶與聯絡人", expanded=True):
        edit_cat = st.selectbox("選擇分類", options=["海外", "貨代", "快遞"], key="edit_cat")
        subs_in_cat = list(st.session_state["contacts_db"].get(edit_cat, {}).keys())

        if not subs_in_cat:
            st.caption("目前此分類尚無已存資料。")
        else:
            edit_sub = st.selectbox("選擇要修改的公司 / 對象", options=subs_in_cat, key="edit_sub")

            # 修改公司名稱或刪除整間公司
            new_company_name = st.text_input(
                "修改公司 / 對象名稱",
                value=edit_sub,
                key=f"rename_sub_{edit_cat}_{edit_sub}",
            )
            btn_col1, btn_col2 = st.columns(2)
            with btn_col1:
                if st.button("✏️ 更新公司名稱", use_container_width=True, key="btn_rename_sub"):
                    clean_new = new_company_name.strip()
                    if clean_new and clean_new != edit_sub:
                        cat_dict = st.session_state["contacts_db"][edit_cat]
                        if clean_new in cat_dict:
                            # 合併底下的國家與聯絡人
                            for ct_k, ppl_v in cat_dict[edit_sub].items():
                                cat_dict[clean_new].setdefault(ct_k, {}).update(ppl_v)
                        else:
                            cat_dict[clean_new] = cat_dict[edit_sub]
                        del cat_dict[edit_sub]
                        st.success(f"已改名為：{clean_new}")
                        st.rerun()
            with btn_col2:
                if st.button("🗑️ 刪除整間公司", use_container_width=True, key="btn_del_sub"):
                    del st.session_state["contacts_db"][edit_cat][edit_sub]
                    st.success(f"已刪除：{edit_sub}")
                    st.rerun()

            st.markdown("---")
            countries_in_sub = list(st.session_state["contacts_db"].get(edit_cat, {}).get(edit_sub, {}).keys())
            if countries_in_sub:
                edit_country = st.selectbox("選擇國家", options=countries_in_sub, key="edit_country")
                people_in_country = list(
                    st.session_state["contacts_db"].get(edit_cat, {}).get(edit_sub, {}).get(edit_country, {}).keys()
                )
                if people_in_country:
                    edit_person = st.selectbox("選擇要修改的聯絡人", options=people_in_country, key="edit_person")
                    cur_info = st.session_state["contacts_db"][edit_cat][edit_sub][edit_country][edit_person]

                    upd_country = st.text_input(
                        "國家 / 地區",
                        value=edit_country,
                        key=f"upd_ct_{edit_cat}_{edit_sub}_{edit_country}_{edit_person}",
                    )
                    upd_person = st.text_input(
                        "聯絡人姓名",
                        value=edit_person,
                        key=f"upd_p_{edit_cat}_{edit_sub}_{edit_country}_{edit_person}",
                    )
                    upd_salutation = st.text_input(
                        "信件開頭稱呼",
                        value=cur_info.get("salutation", ""),
                        key=f"upd_sal_{edit_cat}_{edit_sub}_{edit_country}_{edit_person}",
                    )
                    upd_internal = st.text_input(
                        "職位 / 內部備註（只給你看）",
                        value=cur_info.get("internal_title", ""),
                        key=f"upd_int_{edit_cat}_{edit_sub}_{edit_country}_{edit_person}",
                    )
                    upd_notes = st.text_area(
                        "客戶習慣備註",
                        value=cur_info.get("default_notes", ""),
                        height=60,
                        key=f"upd_note_{edit_cat}_{edit_sub}_{edit_country}_{edit_person}",
                    )

                    p_btn1, p_btn2 = st.columns(2)
                    with p_btn1:
                        if st.button("💾 儲存聯絡人修改", use_container_width=True, key="btn_save_person_edit"):
                            target_ct = upd_country.strip() or edit_country
                            target_p = upd_person.strip() or edit_person
                            sub_dict = st.session_state["contacts_db"][edit_cat][edit_sub]

                            # 刪除舊位置
                            del sub_dict[edit_country][edit_person]
                            if not sub_dict[edit_country]:
                                del sub_dict[edit_country]

                            # 寫入新位置
                            sub_dict.setdefault(target_ct, {})[target_p] = {
                                "salutation": upd_salutation.strip() or f"Hi {target_p}",
                                "internal_title": upd_internal.strip(),
                                "default_notes": upd_notes.strip(),
                            }
                            st.success(f"已更新聯絡人：{target_p}")
                            st.rerun()
                    with p_btn2:
                        if st.button("🗑️ 刪除此聯絡人", use_container_width=True, key="btn_del_person"):
                            sub_dict = st.session_state["contacts_db"][edit_cat][edit_sub]
                            del sub_dict[edit_country][edit_person]
                            if not sub_dict[edit_country]:
                                del sub_dict[edit_country]
                            st.success(f"已刪除聯絡人：{edit_person}")
                            st.rerun()

    with st.expander("🛡️ 固定防呆規則", expanded=False):
        for idx, rule in enumerate(FIXED_GUARDRAILS_ZH, start=1):
            st.markdown(f"**{idx}.** {rule}")


# ================= 主畫面：最上方標題 =================
st.title("貝拉の回信神器")

col_left, col_right = st.columns([1.08, 1.15], gap="large")

with col_left:
    st.subheader("1. 選擇對象與訂單資訊")

    main_cat = st.selectbox(
        "📂 客戶分類",
        options=["海外", "貨代", "快遞"],
        key="sel_main_cat",
        on_change=on_main_cat_change,
    )

    sub_entity = ""
    if main_cat == "海外":
        overseas_companies = list(st.session_state["contacts_db"].get("海外", {}).keys())
        col_o1, col_o2 = st.columns([1.15, 1])
        with col_o1:
            if overseas_companies:
                st.selectbox(
                    "🏢 選擇已存海外客戶（公司名稱）",
                    options=overseas_companies,
                    key="sel_overseas_company",
                    on_change=lambda: on_sub_entity_change("sel_overseas_company"),
                )
            else:
                st.info("目前無已存海外客戶，可在右側直接輸入或由左側新增。")
        with col_o2:
            custom_company_input = st.text_input(
                "✍️ 或直接輸入新客戶公司名稱",
                placeholder="輸入新客戶公司名",
            )
        sub_entity = custom_company_input.strip() or st.session_state.get("sel_overseas_company", "")

    elif main_cat == "貨代":
        forwarder_list = list(st.session_state["contacts_db"].get("貨代", {}).keys())
        if forwarder_list:
            sub_entity = st.selectbox(
                "🏭 選擇貨代公司",
                options=forwarder_list,
                key="sel_forwarder_name",
                on_change=lambda: on_sub_entity_change("sel_forwarder_name"),
            )
        else:
            sub_entity = st.text_input("🏭 輸入貨代公司名稱", placeholder="例如：Forwarder 公司名")

    else:
        courier_options = ["UPS", "FedEx", "DHL"]
        extra_couriers = [
            k for k in st.session_state["contacts_db"].get("快遞", {}).keys() if k not in courier_options
        ]
        sub_entity = st.selectbox(
            "🚚 選擇快遞公司（UPS / FedEx / DHL）",
            options=courier_options + extra_couriers,
            key="sel_courier_carrier",
            on_change=lambda: on_sub_entity_change("sel_courier_carrier"),
        )

    countries_map = st.session_state["contacts_db"].get(main_cat, {}).get(sub_entity, {})
    country_list = list(countries_map.keys()) if countries_map else ["未指定國家"]

    c_col1, c_col2 = st.columns(2)
    with c_col1:
        selected_country = st.selectbox(
            "🌐 國家（自動帶出）",
            options=country_list,
            key="sel_country",
            on_change=lambda: on_country_change(sub_entity),
        )

    contacts_map = countries_map.get(selected_country, {}) if countries_map else {}
    contact_list = list(contacts_map.keys()) if contacts_map else ["（手動輸入聯絡人）"]

    with c_col2:
        selected_contact = st.selectbox(
            "👤 選擇聯絡人",
            options=contact_list,
            key="sel_contact",
            on_change=lambda: on_contact_change(sub_entity),
        )

    if not st.session_state["salutation_val"] and selected_contact != "（手動輸入聯絡人）":
        _sync_from_selection(main_cat, sub_entity, selected_country, selected_contact)

    contact_info = contacts_map.get(selected_contact, {})
    internal_title_val = contact_info.get("internal_title", "")
    contact_habit_note = contact_info.get("default_notes", "")

    if internal_title_val or contact_habit_note:
        info_parts = []
        if internal_title_val:
            info_parts.append(f"**職位/備註：** {internal_title_val}")
        if contact_habit_note:
            info_parts.append(f"**過往習慣：** {contact_habit_note}")
        st.info("🔒 **僅內部參考（不會寫進給客戶的信件）：** " + " ｜ ".join(info_parts))

    salutation_input = st.text_input(
        "✉️ 信件開頭稱呼",
        key="salutation_val",
        placeholder="例如：Dear Chris 或 Hi Mireya",
    )

    po_col1, po_col2 = st.columns(2)
    with po_col1:
        po_input = st.text_input(
            "🔖 PO#（客戶的編號，選填）",
            placeholder="例如：12345 或 PO#12345",
        )
    with po_col2:
        b2pt_input = st.text_input(
            "🏷️ B2PT（我們家的編號，選填）",
            placeholder="例如：2610002 或 B2PT2610002",
        )

    combined_order_code = format_order_code(po_input, b2pt_input)
    if combined_order_code:
        st.caption(f"📌 系統組合單號：**`{combined_order_code}`**")

    st.divider()
    st.subheader("2. 勾選目地與補充細節")

    is_first_meet = st.checkbox("👋 第一次見na～", value=False)

    st.markdown("**選目地（可複選）：**")
    selected_prompts = []
    cb_c1, cb_c2 = st.columns(2)
    for idx, mod in enumerate(ACTION_MODULES):
        target_col = cb_c1 if idx % 2 == 0 else cb_c2
        with target_col:
            if st.checkbox(mod["label"], key=f"chk_{mod['id']}"):
                selected_prompts.append(mod["prompt_zh"])

    is_other_goal = st.checkbox("✏️ 其他（自己輸入想生成的目地）", key="chk_other_goal")
    other_custom_text = ""
    if is_other_goal:
        other_custom_text = st.text_area(
            "其他想生成的目地說明",
            height=75,
            placeholder="輸入你這次想讓系統幫你寫出來的特定內容或需求...",
        )

    st.divider()
    st.markdown("**本次補充細節 / 常用備註（用勾選的，不用每次重打）：**")
    selected_detail_prompts = []
    det_c1, det_c2 = st.columns(2)
    for idx, d_mod in enumerate(COMMON_DETAIL_MODULES):
        target_col = det_c1 if idx % 2 == 0 else det_c2
        with target_col:
            if st.checkbox(d_mod["label"], key=f"chk_{d_mod['id']}"):
                selected_detail_prompts.append(d_mod["prompt_zh"])

    is_other_detail = st.checkbox("➕ 新增其他補充細節（輸入金額、單號或臨時交代）", key="chk_other_detail")
    extra_custom_notes = ""
    if is_other_detail:
        extra_custom_notes = st.text_area(
            "輸入其他補充細節（例如金額、追蹤單號、特殊交代）",
            height=80,
            placeholder="例如：UPS 運費 US$315 / FedEx US$290；Tracking# 1Z999AA10123456784",
        )

    supervisor_advice = st.text_area(
        "👔 主管建議（若主管有交代怎麼回，打在這裡幫你生成）",
        height=80,
        placeholder="例如：主管說先請客人確認數量與寄送方式，運費等確認後再報，不要先承諾交期。",
    )

    customer_email_input = st.text_area(
        "📩 貼上對方來信原文（選填）",
        height=100,
        placeholder="若為回信可貼上對方來信內容；若為主動發信可留空。",
    )

    generate_btn = st.button(
        "🚀 生成英文回信草稿", type="primary", use_container_width=True
    )

with col_right:
    st.subheader("3. 生成結果（點右上角一鍵複製）")

    if generate_btn:
        if not api_key_input.strip():
            st.error("請先在左側欄輸入 Gemini API Key。")
        elif (
            not is_first_meet
            and not selected_prompts
            and not other_custom_text.strip()
            and not selected_detail_prompts
            and not extra_custom_notes.strip()
            and not supervisor_advice.strip()
            and not customer_email_input.strip()
        ):
            st.warning("請至少勾選一個目地或補充細節，或填寫主管建議／來信原文。")
        else:
            with st.spinner("正在整合勾選項目與主管建議生成英文回信..."):
                try:
                    new_res = generate_customer_reply(
                        api_key=api_key_input.strip(),
                        main_cat=main_cat,
                        sub_entity=sub_entity,
                        country=selected_country,
                        contact_name=selected_contact,
                        internal_title=internal_title_val,
                        contact_habit_note=contact_habit_note,
                        salutation=salutation_input,
                        order_code=combined_order_code,
                        is_first_meet=is_first_meet,
                        selected_prompts=selected_prompts,
                        other_custom_text=other_custom_text,
                        supervisor_advice=supervisor_advice,
                        selected_detail_prompts=selected_detail_prompts,
                        extra_custom_notes=extra_custom_notes,
                        customer_email=customer_email_input,
                        model=model_choice,
                    )
                    if st.session_state["last_reply_result"] is not None:
                        st.session_state["prev_reply_result"] = st.session_state["last_reply_result"]
                    st.session_state["last_reply_result"] = new_res
                except Exception as exc:
                    st.error(f"生成失敗：{exc}")

    current_res: EmailReplyOutput | None = st.session_state.get("last_reply_result")
    if current_res is not None:
        st.markdown("**📌 建議主旨（Subject）**")
        st.code(current_res.subject, language=None)

        st.markdown("**✉️ 標準專業版回信**")
        st.code(current_res.standard_reply, language=None)

        st.markdown("**⚡ 簡潔俐落版回信**")
        st.code(current_res.concise_reply, language=None)

        st.markdown("**✅ 中文重點核對清單**")
        for idx, item in enumerate(current_res.zh_checklist, start=1):
            st.markdown(f"- **{idx}.** {item}")
    else:
        st.info("👈 選好客戶公司與聯絡人、勾選目地與補充細節後，點擊 **「生成英文回信草稿」** 即可產出。")

    st.divider()
    prev_res: EmailReplyOutput | None = st.session_state.get("prev_reply_result")
    with st.expander("🕘 上一次的內容", expanded=False):
        if prev_res is not None:
            st.markdown("**📌 上一次主旨（Subject）**")
            st.code(prev_res.subject, language=None)
            st.markdown("**✉️ 上一次標準專業版回信**")
            st.code(prev_res.standard_reply, language=None)
            st.markdown("**⚡ 上一次簡潔俐落版回信**")
            st.code(prev_res.concise_reply, language=None)
        else:
            st.caption("目前還沒有上一次的生成紀錄；再次點擊「生成英文回信草稿」時，前一次的草稿會自動保留在這裡。")

    st.divider()
    st.subheader("💬 有其他想問的？（直接問我）")
    st.caption("外貿英文怎麼寫、單據或快遞怎麼處理、或任何想問的問題，直接輸入就能問。")

    for chat_item in st.session_state["gemini_qa_history"]:
        with st.chat_message("user"):
            st.markdown(chat_item["q"])
        with st.chat_message("assistant"):
            st.markdown(chat_item["a"])

    ask_q = st.text_input(
        "輸入你想問的問題",
        placeholder="例如：這封信如果客人問關稅怎麼回比較客氣？",
        key="free_ask_input",
    )
    if st.button("送出提問", use_container_width=True):
        if not api_key_input.strip():
            st.error("請先在左側欄輸入 Gemini API Key。")
        elif not ask_q.strip():
            st.warning("請先輸入想問的問題。")
        else:
            with st.spinner("正在思考並回覆你的問題..."):
                try:
                    ans = ask_gemini_general(
                        api_key=api_key_input.strip(),
                        question=ask_q.strip(),
                        model=model_choice,
                    )
                    st.session_state["gemini_qa_history"].append(
                        {"q": ask_q.strip(), "a": ans}
                    )
                    st.rerun()
                except Exception as exc:
                    st.error(f"提問失敗：{exc}")
                    
