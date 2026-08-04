from itertools import count

from todo_api.models import Todo, TodoCreate, TodoUpdate


class TodoStore:
    """In-memory todo storage. Not thread-safe; adequate for a sandbox service."""

    def __init__(self) -> None:
        self._items: dict[int, Todo] = {}
        self._ids = count(1)

    def list(self) -> list[Todo]:
        return list(self._items.values())

    def get(self, todo_id: int) -> Todo | None:
        return self._items.get(todo_id)

    def create(self, payload: TodoCreate) -> Todo:
        todo = Todo(id=next(self._ids), title=payload.title, done=payload.done)
        self._items[todo.id] = todo
        return todo

    def update(self, todo_id: int, payload: TodoUpdate) -> Todo | None:
        todo = self._items.get(todo_id)
        if todo is None:
            return None
        updated = todo.model_copy(update=payload.model_dump(exclude_none=True))
        self._items[todo_id] = updated
        return updated

    def delete(self, todo_id: int) -> bool:
        return self._items.pop(todo_id, None) is not None

    def clear(self) -> None:
        self._items.clear()
        self._ids = count(1)
