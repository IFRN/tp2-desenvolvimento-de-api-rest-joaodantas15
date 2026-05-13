# Sistema de Urna Eletrônica API 🗳️

Este projeto consiste em uma API RESTful para gerenciamento de eleições, desenvolvida com **Django REST Framework**. O sistema permite o cadastro de eleitores, candidatos, gestão do ciclo de vida de uma eleição e a realização de votação com garantia de anonimato e emissão de comprovante digital.

## 🛡️ Estratégia de Sigilo e Anonimato (Questão 4)

O requisito mais crítico deste projeto é o **Sigilo do Voto**. Para atender simultaneamente à necessidade de impedir votos duplicados e garantir que ninguém possa rastrear em quem um eleitor votou, foi utilizada a seguinte arquitetura:

### Desacoplamento de Dados
A lógica baseia-se na separação física e lógica de dois registros no momento do voto:

1.  **RegistroVotacao (O "Caderno de Assinaturas"):** Armazena a relação `Eleitor` + `Eleição`. Este registro serve apenas para verificar se o eleitor já compareceu. Ele possui um `unique_together` que impede, via banco de dados, que o mesmo CPF vote duas vezes na mesma eleição.
2.  **Voto (A "Cédula"):** Armazena apenas a `Eleição`, o `Candidato` (ou nulo para branco) e um `comprovante_hash`. **Não existe nenhuma ForeignKey para o Eleitor neste modelo.**

### Garantia de Integridade com SHA-256
Para que o eleitor possa verificar seu voto sem ser identificado:
* No ato do voto, o sistema gera um `secrets.token_urlsafe(32)`.
* Este token é exibido **apenas uma vez** para o eleitor.
* O banco de dados armazena apenas o **Hash SHA-256** desse token.
* Dessa forma, mesmo que alguém tenha acesso total ao banco de dados, é matematicamente impossível reverter o hash para descobrir o token original, e como não há ligação entre o `Voto` e o `RegistroVotacao`, o sigilo é absoluto.

---

## 🚀 Tecnologias Utilizadas

* **Python 3.12**
* **Django 5.0**
* **Django REST Framework**
* **Pillow & Qrcode:** Geração dinâmica de comprovantes.
* **Drf-yasg (Swagger):** Documentação interativa da API.
* **Django Filter:** Filtros avançados em todos os endpoints.

---

## 🛠️ Como rodar o projeto

1. **Instale as dependências:**
   ```bash
   pip install -r requirements.txt

2. Instruções de Migração:rodar python manage.py migrate e python manage.py createsuperuser para criar o próprio acesso se  for rodar localmente.

/admin - será direcionado para o django admin
user e senha 