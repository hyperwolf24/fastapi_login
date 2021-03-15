import pytest
from fastapi import Depends
from starlette.responses import RedirectResponse

from fastapi_login import LoginManager


@pytest.fixture
def custom_exception():
    class CustomAuthException(Exception):
        pass

    return CustomAuthException


@pytest.fixture
def exception_manager(app, secret, token_url, load_user_fn, custom_exception) -> LoginManager:
    instance = LoginManager(secret, token_url)
    instance.user_loader(load_user_fn)

    # exception handling setup

    def redirect_on_auth_exc(request, exc):
        return RedirectResponse(url="/redirect")

    instance.not_authenticated_exception = custom_exception
    app.add_exception_handler(custom_exception, redirect_on_auth_exc)

    # routes
    @app.get("/private/exception")
    def raise_exception(_=Depends(instance)):
        return {"detail": "error"}

    @app.get("/redirect")
    def redirect():
        return {"detail": "Redirected"}

    return instance


@pytest.mark.asyncio
async def test_exception_handling(exception_manager, client, invalid_data):
    invalid_token = exception_manager.create_access_token(data={"sub": invalid_data["username"]})
    resp = await client.get(
        "/private/exception",
        headers={"Authorization": f"Bearer {invalid_token}"}
    )

    assert resp.json()["detail"] == "Redirected"


@pytest.mark.asyncio
async def test_exception_change_no_sub(exception_manager, custom_exception):
    no_sub_token = exception_manager.create_access_token(data={"id": "something"})
    with pytest.raises(custom_exception):
        await exception_manager.get_current_user(no_sub_token)


@pytest.mark.asyncio
async def test_exceptions_change_invalid_token(exception_manager, custom_exception):
    invalid_jwt_token = (
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.aGVsb"
        "G8gd29ybGQ.SIr03zM64awWRdPrAM_61QWsZchAtgDV"
        "3pphfHPPWkI"
    )  # this token is taken from pyjwt (https://github.com/jpadilla/pyjwt/blob/master/tests/test_api_jwt.py#L82)
    with pytest.raises(custom_exception):
        await exception_manager.get_current_user(invalid_jwt_token)


@pytest.mark.asyncio
async def test_exceptions_change_user_is_none(exception_manager, custom_exception, invalid_data):
    invalid_user_token = exception_manager.create_access_token(data={"sub": invalid_data["username"]})
    with pytest.raises(custom_exception):
        await exception_manager.get_current_user(invalid_user_token)
