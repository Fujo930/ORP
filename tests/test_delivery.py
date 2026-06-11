"""Tests for ORP delivery"""

from orp.schema import Lesson, DeliveryStrategy
from orp.storage import ORPStorage
from orp.delivery import DeliveryRouter


def test_mcp_tools():
    router = DeliveryRouter()
    tools = router.get_mcp_tools()
    assert len(tools) == 3
    names = [t["name"] for t in tools]
    assert "orp_retrieve_lessons" in names
    assert "orp_acknowledge_lesson" in names
    assert "orp_report_outcome" in names
