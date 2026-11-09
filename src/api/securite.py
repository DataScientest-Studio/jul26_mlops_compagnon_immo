
#Sécurité OAuth2 + JWT pour les API Compagnon Immobilier

import os
from datetime import datetime, timedelta, timezone

import jwt
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash

load_dotenv()

SECRET_KEY = os.environ["JWT_SECRET_KEY"]
ALGORITHM = "HS256"

password_hash = PasswordHash.recommended()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
router = APIRouter()

# Deux utilisateurs (admin et user)
UTILISATEURS = {
    "admin": {
        "password_hash": os.environ["ADMIN_PASSWORD_HASH"],
        "role": "admin",
    },
    "user": {
        "password_hash": os.environ["USER_PASSWORD_HASH"],
        "role": "user",
    },
}


# Authentification et création du token
@router.post("/token")
def login(form: OAuth2PasswordRequestForm = Depends()):
    utilisateur = UTILISATEURS.get(form.username)

    if (
        utilisateur is None
        or not password_hash.verify(
            form.password, utilisateur["password_hash"]
        )
    ):
        raise HTTPException(
            status_code=401,
            detail="Identifiants incorrects",
            headers={"WWW-Authenticate": "Bearer"},
        )

    expiration = datetime.now(timezone.utc) + timedelta(minutes=30)

    token = jwt.encode(
        {
            "sub": form.username,
            "iss": "compagnon-immobilier",
            "aud": "compagnon-api",
            "exp": expiration,
        },
        SECRET_KEY,
        algorithm=ALGORITHM,
    )

    return {"access_token": token, "token_type": "bearer"}


# Vérification du token
def verifier_token(token: str = Depends(oauth2_scheme)):
    try:
        donnees = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            issuer="compagnon-immobilier",
            audience="compagnon-api",
            options={"require": ["sub", "exp", "iss", "aud"]},
        )

        username = donnees["sub"]
        utilisateur = UTILISATEURS.get(username)

        if utilisateur is None:
            raise ValueError("Utilisateur inexistant")

        return utilisateur

    except (InvalidTokenError, ValueError):
        raise HTTPException(
            status_code=401,
            detail="Token invalide ou expiré",
            headers={"WWW-Authenticate": "Bearer"},
        )


# Autorisation profil admin
def verifier_admin(utilisateur=Depends(verifier_token)):
    if utilisateur["role"] != "admin":
        raise HTTPException(
            status_code=403,
            detail="Accès réservé à l'administrateur",
        )
    return utilisateur


# Autorisation profil user ou admin
def verifier_utilisateur(utilisateur=Depends(verifier_token)):
    if utilisateur["role"] not in ("user", "admin"):
        raise HTTPException(status_code=403, detail="Accès refusé")
    return utilisateur
