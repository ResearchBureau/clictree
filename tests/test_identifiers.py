import pytest

from clictree.identifiers import URI


@pytest.mark.parametrize(
    "string_in, expected, is_absolute",
    [
        ("123",
         URI(context_name=None, domain_name=None, container_name=None,
             data_item_uid='123'),False),
        ("container/123",
         URI(context_name=None, domain_name=None, container_name="container",
             data_item_uid='123'),False),
        ("domain/container/123",
         URI(context_name=None, domain_name="domain", container_name="container",
             data_item_uid='123'),False),
        ("local/domain/container/123",
         URI(context_name="local", domain_name="domain", container_name="container",
             data_item_uid='123'),True),
        ("/local/domain/container/123",
         URI(context_name="local", domain_name="domain", container_name="container",
             data_item_uid='123'),True),
        ("/local/domain",
         URI(context_name="local", domain_name="domain", container_name=None,
             data_item_uid=None),True)
    ]
)
def test_uri(string_in, expected, is_absolute):
    assert URI.from_string(string_in) == expected
    assert URI.from_string(string_in).is_absolute() == is_absolute