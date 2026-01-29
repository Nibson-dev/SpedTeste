# SPED Parser:  (Laboratório de Lógica)

> **"Para construir um arranha-céu, primeiro você precisa entender o tijolo."**
> Este repositório contém os primeiros scripts experimentais criados para decifrar a estrutura lógica do SPED Fiscal (EFD ICMS/IPI).

---

##  Status: Arquivo Histórico (Prototype)
**Este código não é um produto.** É um estudo de caso bruto, preservado para documentar como a lógica de leitura dos arquivos fiscais brasileiros foi descoberta e mapeada antes de criarmos os sistemas robustos (ConciliadorVALE e V1 Azure).

---

##  O Cenário Inicial
O arquivo SPED é um monstro de texto: milhões de linhas, separadas por pipes (`|`), com uma hierarquia complexa de blocos (0, C, E, H, etc.).
Antes de tentar automatizar auditorias ou criar interfaces visuais, precisávamos responder a perguntas fundamentais de Engenharia de Dados:

1.  Como o Python lida com arquivos de texto de 2GB+?
2.  Qual a melhor estratégia para "quebrar" (parse) as linhas separadas por `|`?
3.  Como relacionar um "Pai" (ex: Nota Fiscal C100) com seus "Filhos" (ex: Itens C170) programaticamente?

---

##  O Experimento
Este projeto não usava Banco de Dados nem Interface Gráfica. Ele era **Python Puro** contra **Texto Bruto**.

### O que este código faz (Lógica Base):
* **Leitura de Streams:** Testes de leitura linha-a-linha para não estourar a memória RAM (o início da lógica de "chunks").
* **Mapeamento de Blocos:** Scripts simples que varrem o arquivo contando quantas notas (C100) ou apurações (E110) existem.
* **Decodificador de Layout:** A primeira tentativa de transformar o "layout Guia Prático da Receita" em dicionários Python.

---

##  Aprendizados Cruciais
Foi aqui que descobrimos os pilares que sustentam as versões atuais:

* **A "Armadilha" do Encoding:** Descobrimos na prática a dor de cabeça do `latin-1` vs `utf-8` nos arquivos do governo.
* **A Estrutura de Árvore:** Entendemos que o SPED não é uma tabela plana, mas uma árvore hierárquica (Header -> Nota -> Item -> Tributo).
* **Performance:** Aprendemos que `pandas.read_csv` com separador `|` funciona, mas precisa de tratamento especial para colunas vazias.

---

##  Tech Stack (Minimalista)

* **Linguagem:** Python 3.x
* **Libs:** `pandas` (para testes estruturados) e `csv` (para testes de velocidade bruta).
* **Input:** Arquivos `.txt` (Layout SPED Fiscal).

---

##  O Legado
Este código é "feio", sem tratamento de erro e sem interface. Mas foi ele que provou que **era possível**.
A lógica desenvolvida aqui serviu de base para:
1.  A automação visual do **PVA na Azure (V1)**.
2.  O motor de alta performance do **ConciliadorVALE (V2)**.

---

##  Autor

Estudo realizado por **Nibson Muller**.
*Documentando a jornada de transformar burocracia em código.*
