import pytest

from prisma import Prisma, errors
from prisma.models import Post, User
from prisma.partials import PostOnlyPublished

from ..utils import RawQueries, DatabaseConfig


def test_query_raw(
    client: Prisma,
    raw_queries: RawQueries,
    config: DatabaseConfig,
) -> None:
    """Standard usage, erroneous query and correct queries"""
    with pytest.raises(errors.RawQueryError):
        client.query_raw(raw_queries.select_unknown_table)

    post = client.post.create(
        {
            'title': 'My post title!',
            'published': False,
        }
    )

    results = client.query_raw(raw_queries.count_posts)
    assert len(results) == 1
    assert isinstance(results[0]['count'], int)

    results = client.query_raw(raw_queries.find_post_by_id, post.id)
    assert len(results) == 1
    assert results[0]['id'] == post.id
    if config.bools_are_ints:
        assert results[0]['published'] == 0
    else:
        assert results[0]['published'] is False


def test_query_raw_model(
    client: Prisma,
    raw_queries: RawQueries,
) -> None:
    """Transforms resuls to a BaseModel when given"""
    post = client.post.create(
        {
            'title': 'My post title!',
            'published': False,
        }
    )

    posts = client.query_raw(raw_queries.find_post_by_id, post.id, model=Post)
    assert len(posts) == 1

    found = posts[0]
    assert isinstance(found, Post)
    assert found == post
    assert found.id == post.id


def test_query_raw_partial_model(
    client: Prisma,
    raw_queries: RawQueries,
) -> None:
    """Transforms results to a partial model"""
    posts = [
        client.post.create({'title': 'foo', 'published': False}),
        client.post.create({'title': 'foo', 'published': True}),
        client.post.create({'title': 'foo', 'published': True}),
        client.post.create({'title': 'foo', 'published': False}),
    ]
    results = client.query_raw(
        raw_queries.find_posts_not_published,
        model=PostOnlyPublished,
    )
    assert len(results) == 2
    assert {p.id for p in results} == {p.id for p in posts if p.published is False}
    assert not hasattr(results[0], 'title')
    assert results[0].published is False
    assert results[1].published is False


def test_query_raw_no_result(
    client: Prisma,
    raw_queries: RawQueries,
) -> None:
    """No result returns empty list"""
    results = client.query_raw(raw_queries.test_query_raw_no_result)
    assert len(results) == 0

    results = client.query_raw(
        raw_queries.test_query_raw_no_result,
        model=Post,
    )
    assert len(results) == 0


@pytest.mark.skip(reason='Disabled as this test broke with prisma v5.15.0 - pending resolution with their team')
def test_query_raw_incorrect_params(
    client: Prisma,
    raw_queries: RawQueries,
    config: DatabaseConfig,
) -> None:
    """Passings too many parameters raises an error"""
    if config.id == 'mysql':
        pytest.skip(
            'Passing the incorrect number of query parameters breaks subsequent queries',
        )

    results = client.query_raw(raw_queries.count_posts)
    assert len(results) == 1
    assert results[0]['count'] == 0

    # SQLite raises RawQueryError
    # PostgreSQL raises DataError
    with pytest.raises((errors.RawQueryError, errors.DataError)):
        client.query_raw(raw_queries.count_posts, 1)

    # subsequent queries can still be made
    results = client.query_raw(raw_queries.count_posts)
    assert len(results) == 1
    assert results[0]['count'] == 0


def test_execute_raw(client: Prisma, raw_queries: RawQueries) -> None:
    """Basic usage"""
    post = client.post.create(
        {
            'title': 'My post title.',
            'published': False,
        }
    )
    assert isinstance(post.id, str)

    count = client.execute_raw(
        raw_queries.update_unique_post_title,
        post.id,
    )
    assert count == 1

    found = client.post.find_unique(where={'id': post.id})
    assert found is not None
    assert found.id == post.id
    assert found.title == 'My edited title'


def test_execute_raw_no_result(
    client: Prisma,
    raw_queries: RawQueries,
) -> None:
    """No result returns 0"""
    count = client.execute_raw(raw_queries.test_execute_raw_no_result)
    assert count == 0


def test_query_first(
    client: Prisma,
    raw_queries: RawQueries,
) -> None:
    """Standard usage"""
    user = client.user.create({'name': 'Robert'})

    found = client.query_first(raw_queries.find_user_by_id, user.id)
    assert found['id'] == user.id
    assert found['name'] == 'Robert'


def test_query_first_model(
    client: Prisma,
    raw_queries: RawQueries,
) -> None:
    """Transforms result to a BaseModel if given"""
    user = client.user.create({'name': 'Robert'})

    found = client.query_first(
        raw_queries.find_user_by_id,
        user.id,
        model=User,
    )
    assert found is not None
    assert found.id == user.id
    assert found.name == 'Robert'
