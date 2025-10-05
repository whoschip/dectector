from supabase import create_client, Client


class SupaDB:
    def __init__(self, url: str, key: str):
        self.url = url
        self.key = key
        self.client: Client = create_client(self.url, self.key)

    def insert(self, table: str, data: dict):
        return self.client.table(table).insert(data).execute()

    def fetch_all(self, table: str):
        return self.client.table(table).select("*").execute()

    def fetch_by_id(self, table: str, row_id: int):
        return self.client.table(table).select("*").eq("id", row_id).execute()

    def update(self, table: str, data: dict, filters: dict):
        query = self.client.table(table).update(data)
        for col, val in filters.items():
            query = query.eq(col, val)
        return query.execute()

    def delete(self, table: str, filters: dict):
        # filters: {column: value, ...}
        query = self.client.table(table).delete()
        for col, val in filters.items():
            query = query.eq(col, val)
        return query.execute()

    def select(self, table: str, filters: dict):
        query = self.client.table(table).select("*")
        for col, val in filters.items():
            query = query.eq(col, val)
        res = query.execute()
        if hasattr(res, "data"):
            return res.data
        return []
