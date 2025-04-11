# File: common/utils/pagination.py

from math import ceil
from typing import Any, List, Dict


def paginate_response(
    items: List[Any],
    total: int,
    page: int = 1,
    page_size: int = 20
) -> Dict[str, Any]:
    """
    Build a standard pagination response.

    Args:
        items (List[Any]): List of results.
        total (int): Total number of items.
        page (int): Current page number.
        page_size (int): Number of items per page.

    Returns:
        Dict[str, Any]: Standardized paginated response.
    """
    return {
        "items": items,
        "meta": {
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": ceil(total / page_size) if page_size > 0 else 0
        }
    }