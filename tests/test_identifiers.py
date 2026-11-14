import pytest

from clictree.identifiers import URI, URIReferenceLevel, URIScope


@pytest.mark.parametrize(
    "string_in, expected, is_absolute",
    [
        ("123",
         URI(context_name=None, domain_name=None, container_name=None,
             data_item_uid='123'),False),
        ("container:123",
         URI(context_name=None, domain_name=None, container_name="container",
             data_item_uid='123'),False),
        ("domain:container:123",
         URI(context_name=None, domain_name="domain", container_name="container",
             data_item_uid='123'),False),
        ("local:domain:container:123",
         URI(context_name="local", domain_name="domain", container_name="container",
             data_item_uid='123'),True),
        ("/local:domain:container:123",
         URI(context_name="local", domain_name="domain", container_name="container",
             data_item_uid='123'),True),
        ("/local:domain",
         URI(context_name="local", domain_name="domain", container_name=None,
             data_item_uid=None),True),
        ("/:domain:container",
         URI(context_name=None, domain_name="domain", container_name="container",
             data_item_uid=None),False)
    ]
)
def test_uri(string_in, expected, is_absolute):
    assert URI.from_string(string_in) == expected
    assert URI.from_string(string_in).is_absolute() == is_absolute


@pytest.mark.parametrize(
    "string_in, level_expected, scope_expected",
    [
        ("123",URIReferenceLevel.DATA_ITEM, URIScope.DATA_ITEM),
        ("container:123",URIReferenceLevel.DATA_ITEM, URIScope.CONTAINER),
        ("domain:container:123",URIReferenceLevel.DATA_ITEM, URIScope.DOMAIN),
        ("context:domain:container:123",URIReferenceLevel.DATA_ITEM, URIScope.CONTEXT),
        ("/context:domain:container:123", URIReferenceLevel.DATA_ITEM, URIScope.CONTEXT),
        ("/context:domain:container", URIReferenceLevel.CONTAINER, URIScope.CONTEXT),
        ("/context:domain", URIReferenceLevel.DOMAIN, URIScope.CONTEXT),
        ("/context", URIReferenceLevel.CONTEXT, URIScope.CONTEXT),


    ]
)
def test_uri_scope(string_in, level_expected, scope_expected):
    uri = URI.from_string(string_in)
    assert uri.scope() == scope_expected
    assert uri.reference_level() == level_expected