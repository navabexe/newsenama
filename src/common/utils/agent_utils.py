# File: src/common/utils/agent_utils.py

from user_agents import parse

def parse_user_agent(user_agent: str) -> dict:
    agent = parse(user_agent)

    return {
        "device_type": "Mobile" if agent.is_mobile else "Tablet" if agent.is_tablet else "PC" if agent.is_pc else "Other",
        "os": agent.os.family or "Unknown",
        "browser": agent.browser.family or "Unknown",
        "device_name": agent.device.family or "Unknown Device"
    }
