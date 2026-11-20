"""Tests unitaires minimaux pour les fonctions de generation d'images et HTML/PDF."""

import sys
import os
import re
from unittest.mock import patch

# Ajoute le repertoire racine au path pour pouvoir importer app_desktop
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app_desktop
from app_desktop import _is_image_creation_request, _looks_like_html


def test_is_image_creation_request_detecte_verbe_plus_sujet():
    assert _is_image_creation_request("genere une image de chat") is True
    assert _is_image_creation_request("dessine un dessin de chat") is True
    assert _is_image_creation_request("cree un dessin d'un chaton") is True


def test_is_image_creation_request_sujet_de_d_dette():
    assert _is_image_creation_request("dessin d'oiseau") is True
    assert _is_image_creation_request("image de chat") is True


def test_is_image_creation_request_non_image():
    assert _is_image_creation_request("ecris un PDF sur les chats") is False
    assert _is_image_creation_request("quelle est la capitale de la France ?") is False
    assert _is_image_creation_request("") is False


def test_looks_like_html_vrai_pour_document_html():
    assert _looks_like_html("<!DOCTYPE html><html></html>") is True
    assert _looks_like_html("<html><body>test</body></html>") is True


def test_looks_like_html_faux_pour_markdown():
    assert _looks_like_html("# Titre en markdown") is False
    assert _looks_like_html("Parle de <html> mais ce n'est pas du HTML") is False


@patch("app_desktop.ollama.chat")
def test_build_flux_prompt_retourne_prompt_anglais(mock_chat):
    mock_chat.return_value = {"message": {"content": "a cat sitting on a mat"}}

    app = object.__new__(app_desktop.App)
    request = {
        "history": [
            {"role": "user", "content": "un chat sur un tapis"},
        ],
        "image_generator_available": True,
    }
    result = app_desktop.App._build_flux_prompt(app, "qwen2.5:7b", request)
    assert result == "a cat sitting on a mat"
    mock_chat.assert_called_once()


@patch("app_desktop.ollama.chat")
def test_build_flux_prompt_coloriage_ajoute_mots_cles(mock_chat):
    mock_chat.return_value = {"message": {"content": "animaux de la savane"}}

    app = object.__new__(app_desktop.App)
    request = {
        "history": [
            {"role": "user", "content": "coloriage pour enfant animaux de la savane"},
        ],
        "image_generator_available": True,
    }
    result = app_desktop.App._build_flux_prompt(app, "qwen2.5:7b", request)
    assert "coloring" in result.lower() or "children coloring page" in result.lower()
    assert "outline" in result.lower() or "line art" in result.lower()


if __name__ == "__main__":
    test_is_image_creation_request_detecte_verbe_plus_sujet()
    test_is_image_creation_request_sujet_de_d_dette()
    test_is_image_creation_request_non_image()
    test_looks_like_html_vrai_pour_document_html()
    test_looks_like_html_faux_pour_markdown()
    test_build_flux_prompt_retourne_prompt_anglais()
    test_build_flux_prompt_coloriage_ajoute_mots_cles()
    print("Tous les tests passent.")
