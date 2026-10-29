import json
import traceback
from sqlalchemy.orm import Session

from openai import OpenAI

from app.common.exceptions import BusinessException
from app.config import settings
from app.schemas.ai import ChatRequest
from app.services import equipment_service, kb_service, lab_service


SYSTEM_PROMPT = """你是智能实验室预约系统的助手，回答要简洁。
如果下面提供了实验室资料，请依据资料回答规则、安全、文档里的开放时间说明。
查询当前有哪些开放实验室、某实验室有哪些设备时，必须调用工具，不要编造。
如果用户想查询某实验室的设备，且你不知道该实验室的ID，请务必先调用 list_open_labs 工具获取实验室ID，再调用 list_lab_equipments 工具查询设备。
你不能替用户提交预约，也不能直接改数据库。
如果用户要预约，请说明去「实验室列表」选择后提交，等待管理员审核。
"""


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_open_labs",
            "description": "查询当前开放中的实验室列表，可以按名称关键字来筛选",
            "parameters": {
                "type": "object",
                "properties": {
                    "keywords": {
                        "type": "string",
                        "description": "实验室的名称关键字，可以为空",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_lab_equipments",
            "description": "查询某个实验室下的设备列表",
            "parameters": {
                "type": "object",
                "properties": {
                    "lab_id": {
                        "type": "integer",
                        "description": "实验室 ID",
                    },
                    "keywords": {
                        "type": "string",
                        "description": "实验室设备名称的关键字，可以为空",
                    },
                },
                "required": ["lab_id"]  # 强制要求大模型必须传 lab_id
            },
        },
    }
]


def run_tool(db: Session, name: str, arguments: str) -> str:
    try:
        args = json.loads(arguments or "{}")
    except json.JSONDecodeError:
        return json.dumps({"error": "参数不是合法的json"}, ensure_ascii=False)

    try:
        if name == "list_open_labs":
            keywords = (args.get("keywords") or "").strip() or None
            page = lab_service.get_lab_page_list(db, page=1, page_size=10, keywords=keywords, status=1)
            rows = [
                {
                    "id": item.id,
                    "name": item.name,
                    "location": item.location,
                    "capacity": item.capacity,
                    "open_time": item.open_time,
                    "close_time": item.close_time
                }
                for item in page.list
            ]
            return json.dumps({"total": page.total, "labs": rows}, ensure_ascii=False)
        
        if name == "list_lab_equipments": 
            lab_id = args.get("lab_id")
            if not lab_id:
                return json.dumps({"error": "缺少参数lab_id。请先调用 list_open_labs 工具获取实验室的ID，然后再查询设备。"}, ensure_ascii=False)
            
            try:
                lab_id = int(lab_id)
            except ValueError:
                return json.dumps({"error": f"lab_id必须为整数，你提供的值为 {lab_id}"}, ensure_ascii=False)
                
            keywords = (args.get("keywords") or "").strip() or None
            
            # 👇 核心修复：调用正确的方法名，并去掉不支持的 status 参数
            page = equipment_service.get_equipment_page_list(
                db, page=1, page_size=10, lab_id=lab_id, keywords=keywords
            )
            
            # 👇 核心修复：根据 equipment_service.py 返回的 EquipmentResponse 字段进行映射
            rows = [
                {
                    "id": item.id,
                    "name": item.name,
                    "lab_id": getattr(item, 'equipment_id', None),    # 对应 service 里的 res.equipment_id
                    "lab_name": getattr(item, 'equipment_name', None), # 对应 service 里的 res.equipment_name
                    "spec": getattr(item, 'spec', None),              
                    "quantity": getattr(item, 'quantity', None),
                    "status": getattr(item, 'status', None),
                }
                for item in page.list
            ]
            return json.dumps({"total": page.total, "equipments": rows}, ensure_ascii=False)

        return json.dumps({"error": f"未找到工具：{name}"}, ensure_ascii=False)
    except Exception as exc:
        # 打印详细的堆栈信息到终端，方便排查具体是哪个字段或查询导致的崩溃
        traceback.print_exc()
        return json.dumps({"error": f"查询服务出现异常: {str(exc)}"}, ensure_ascii=False)


def get_client() -> OpenAI:
    """创建OPENAI的客户端"""
    if not settings.LLM_API_KEY:
        raise BusinessException(message="未获取到大模型的API Key")
    return OpenAI(api_key=settings.LLM_API_KEY, base_url=settings.LLM_BASE_URL)


def chat(db: Session, data: ChatRequest):
    if not data.messages:
        raise BusinessException(message="对话内容为空")
        
    history = []
    for message in data.messages:
        if message.role in ("user", "assistant") and message.content.strip():
            history.append(message.model_dump())
            
    if not history:
        raise BusinessException(message="请输入您要对话的内容")

    question = next(
        (item["content"] for item in reversed(history) if item["role"] == "user"), ""
    )
    
    # 检索知识库
    knowledge = kb_service.search(query=question)
    system_prompt = SYSTEM_PROMPT
    if knowledge:
        system_prompt += "\n\n以下是检索到的实验室的资料:\n" + str(knowledge)

    client = get_client()
    
    # 将 system_prompt 变量正确传入
    messages = [{"role": "system", "content": system_prompt}, *history]
    
    try:
        for _ in range(3):
            res = client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto"
            )
            msg = res.choices[0].message
            tool_calls = msg.tool_calls or []
            
            if not tool_calls:  # 没有工具调用 则直接返回大模型的输出结果内容
                content = msg.content
                if not content or not content.strip():
                    raise BusinessException(message="大模型没有返回内容")
                return content
                
            # 将助手的工具调用请求加入上下文
            messages.append(
                {
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": [
                        {
                            "id": call.id, 
                            "type": "function",
                            "function": {
                                "name": call.function.name, 
                                "arguments": call.function.arguments
                            }
                        } for call in tool_calls
                    ],
                }
            )
            
            # 执行工具并将结果加入上下文
            for call in tool_calls:
                result = run_tool(db, call.function.name, call.function.arguments)
                messages.append(
                    {"role": "tool", "content": result, "tool_call_id": call.id}
                )

        # 连续 3 轮都是工具调用，没有产出最终回复
        raise BusinessException(message="大模型未能给出回复，请稍后重试")
    except BusinessException:
        raise
    except Exception:
        traceback.print_exc()
        raise BusinessException(message="大模型调用失败，请稍后重试")