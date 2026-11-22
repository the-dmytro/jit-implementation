from jit_implementation.ide import IDE


class Widget:
    pass


def uses_widget(w: Widget) -> int:
    return 0


def uses_widget_list(items: list[Widget]) -> None:
    pass


class Service:
    def handle(self, w: Widget) -> int:
        return 0


def test_collects_custom_types_from_function():
    ide = IDE(uses_widget)
    assert Widget in ide.unread_types
    assert int not in ide.unread_types


def test_collects_types_from_generic_annotations():
    ide = IDE(uses_widget_list)
    assert Widget in ide.unread_types
    assert list not in ide.unread_types


def test_collects_types_from_class_methods():
    ide = IDE(Service)
    assert Widget in ide.unread_types


def test_read_source_caches_and_clears_unread():
    ide = IDE(uses_widget)
    source = ide.read_source(Widget)
    assert "class Widget" in source
    assert Widget not in ide.unread_types
    assert ide.read_source(Widget) is source
