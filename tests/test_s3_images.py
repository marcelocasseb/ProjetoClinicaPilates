"""Testes do helper de S3 das imagens (IMG-06, IMG-08)."""
import boto3

from app import s3_images


def test_content_type_valido():
    assert s3_images.content_type_valido("image/jpeg")
    assert s3_images.content_type_valido("image/png")
    assert s3_images.content_type_valido("image/webp")
    assert not s3_images.content_type_valido("application/pdf")
    assert not s3_images.content_type_valido("image/gif")


def test_montar_key_isola_e_usa_extensao():
    assert s3_images.montar_key("c1", "p1", "img1", "image/jpeg") == "c1/p1/img1.jpg"
    assert s3_images.montar_key("c1", "p1", "img1", "image/png") == "c1/p1/img1.png"
    assert s3_images.montar_key("c1", "p1", "img1", "image/webp") == "c1/p1/img1.webp"


def test_url_upload_e_download_apontam_para_o_bucket(imagens_ambiente):
    key = "c1/p1/img1.png"
    up = s3_images.url_upload(key, "image/png")
    down = s3_images.url_download(key)
    assert imagens_ambiente in up and "img1.png" in up
    assert imagens_ambiente in down and "img1.png" in down


def test_objeto_existe_e_apagar(imagens_ambiente):
    key = "c1/p1/img1.png"
    assert s3_images.objeto_existe(key) is False
    boto3.client("s3", region_name="us-east-1").put_object(
        Bucket=imagens_ambiente, Key=key, Body=b"fake"
    )
    assert s3_images.objeto_existe(key) is True
    s3_images.apagar(key)
    assert s3_images.objeto_existe(key) is False
