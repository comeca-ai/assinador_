import re
from pydantic import BaseModel, Field, ConfigDict, field_validator

class Model(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)

class Credentials(Model):
    email: str=Field(min_length=3,max_length=254)
    password: str=Field(min_length=12,max_length=128)
    @field_validator('email')
    @classmethod
    def email_check(cls,v):
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',v): raise ValueError('E-mail inválido')
        return v.casefold()

class Register(Credentials):
    name: str=Field(min_length=2,max_length=100)
    organization: str=Field(min_length=2,max_length=100)

class OrgInput(Model):
    name: str=Field(min_length=2,max_length=100)

class Brand(Model):
    brand_name: str=Field(min_length=2,max_length=80)
    color: str=Field(pattern=r'^#[0-9a-fA-F]{6}$')

class SignerInput(Model):
    name: str=Field(min_length=2,max_length=100)
    email: str=Field(min_length=3,max_length=254)
    @field_validator('email')
    @classmethod
    def email_check(cls,v): return Credentials.email_check(v)

class TokenInput(Model):
    token: str=Field(min_length=40,max_length=64,pattern=r'^[A-Za-z0-9_-]+$')

class ConsentInput(TokenInput):
    accepted: bool
    terms_version: str=Field(max_length=60)

class ConfirmInput(TokenInput):
    declared_name: str=Field(min_length=2,max_length=100)
    original_sha256: str=Field(pattern=r'^[0-9a-f]{64}$')

class TemplateInput(Model):
    name: str=Field(min_length=2,max_length=100)
    body: str=Field(min_length=5,max_length=20000)

class MemberInput(Model):
    email: str=Field(max_length=254)
    role: str=Field(pattern=r'^(admin|member|viewer)$')
    @field_validator('email')
    @classmethod
    def email_check(cls,v): return Credentials.email_check(v)

class PasswordChange(Model):
    current_password: str=Field(min_length=12,max_length=128)
    new_password: str=Field(min_length=12,max_length=128)
