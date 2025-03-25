def get_pagination_params(page: int = 1, page_size: int = 20):
    skip = (page - 1) * page_size
    limit = page_size
    return skip, limit
