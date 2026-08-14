# Tokens de tema — claro e escuro

Referência de como lidar com cor em `.vue`, `.less` e templates que a skill gerar ou
editar num projeto `jeecgboot-vue3`.

Este documento **não lista valores de cor de propósito**. Os valores vivem no projeto e
mudam com o tema — a skill deve lê-los de lá, nunca de uma cópia congelada aqui.

## Regra dura

**Nunca escreva cor literal em `<style>` de tela.** Nada de `#fff`, `#fafafa`, `#262626`,
`rgba(0, 0, 0, 0.65)`, `white`, `black`. Cada literal é um bug de dark mode: no escuro
vira painel branco com texto claro (ilegível) ou texto quase preto sobre fundo escuro
(invisível).

Use sempre uma CSS var `--dc-*`. Elas já carregam o par claro/escuro.

## Passo 1 — Descubra os tokens no projeto

Antes de escrever qualquer cor, leia a definição real:

```
src/design/dc-tokens.less
```

Esse arquivo define cada token duas vezes: no `:root` (tema claro) e dentro do bloco
`html[data-theme='dark']` (tema escuro). Se não encontrar o caminho, localize com Glob
(`**/design/dc-tokens.less`) ou busque por `--dc-` no `src/`.

Outros pontos de referência, quando precisar entender o mecanismo:

| Arquivo | O que tem |
|---|---|
| `src/design/dc-tokens.less` | **fonte da verdade** dos `--dc-*`, claro e escuro |
| `src/design/theme.less` | paleta crua do escuro, insumo dos `--dc-*` |
| `src/logics/theme/dark.ts` | seta o atributo `html[data-theme='dark']` |
| `src/App.vue` | tokens do ConfigProvider e correção de contraste do accent em runtime |
| `src/settings/designSetting.ts` | espelho da paleta escura — mexeu em uma, mexa na outra |

Liste os tokens disponíveis com uma busca por `--dc-` nesse arquivo antes de inventar
nome novo.

## Por que as vars LESS não servem

O projeto tem três camadas de cor e **só uma** reage ao toggle de tema:

| Camada | Troca no dark? |
|---|---|
| Vars LESS (`@primary-color`, `@component-background`, `@white`, `@text-color`, `@border-color-base`), injetadas em todo `<style lang="less">` pelo build | **NÃO.** São compiladas uma única vez com os valores do tema claro, congeladas no bundle. |
| Tokens do ConfigProvider (`colorBgContainer`, `colorText`, `colorBorder`…) | Sim, mas **perdem para `<style scoped>` e `:deep()`**, que têm especificidade maior. |
| **CSS vars `--dc-*`** | **Sim — e é a única que continua valendo dentro de `<style scoped>`.** |

Nada em `<style scoped>` reage ao `data-theme` por conta própria. Só via `--dc-*`.

## Passo 2 — Escolha o token pelo papel

Use o token cujo **papel** corresponde ao uso. Os valores concretos você já leu do
`dc-tokens.less`.

| Família | Papel |
|---|---|
| `--dc-bg` | fundo da área de conteúdo, atrás dos cards |
| `--dc-surface` | card, painel, modal, célula |
| `--dc-surface-2` | faixa elevada: header de tabela, toolbar, linha zebrada |
| `--dc-surface-3` | hover, área rebaixada, fundo de agrupamento |
| `--dc-border` | divisórias |
| `--dc-border-strong` | contorno de controle ou card destacado |
| `--dc-text` | texto principal e títulos |
| `--dc-text-2` | texto de apoio |
| `--dc-text-3` | rótulo, hint, placeholder |
| `--dc-accent` | cor de marca em texto, link e destaque |
| `--dc-accent-bg` / `--dc-accent-border` | fundo e borda de destaque |
| `--dc-success` / `--dc-error` / `--dc-warning` / `--dc-info` | semânticos |

**Semânticos vêm em trio** `-text` / `-bg` / `-border` (ex.: `--dc-error-text`,
`--dc-error-bg`, `--dc-error-border`). O token puro é só para ícone ou badge sólido.

**Sempre `--dc-accent`, nunca a var de primary do System theme direto** em texto ou link:
a cor crua de marca costuma não alcançar contraste legível sobre a superfície escura. O
`--dc-accent` aponta para a versão já corrigida em runtime.

## Vars de baixo nível — não usar em tela

- `--dc-dark-*` — paleta crua do escuro. **Só existem sob `[data-theme='dark']`**: usadas
  direto, somem no tema claro. São insumo dos `--dc-*`, não API de tela.
- `--header-*`, `--sider-*` — chrome do layout, geridas em runtime. Não usar em tela de
  conteúdo.

## Padrão correto

```vue
<style lang="less" scoped>
  .painel {
    background: var(--dc-surface);
    border: 1px solid var(--dc-border);
    color: var(--dc-text);
  }
  .painel__cabecalho { background: var(--dc-surface-2); }
  .painel__linha:hover { background: var(--dc-surface-3); }
  .painel__rotulo { color: var(--dc-text-3); }
  .painel__valor { color: var(--dc-accent); }

  .tag-erro {
    color: var(--dc-error-text);
    background: var(--dc-error-bg);
    border: 1px solid var(--dc-error-border);
  }
</style>
```

## Antipadrões

```less
background: #fff;                          // some no escuro
background: @component-background;         // var LESS: congelada no claro
color: rgba(0, 0, 0, 0.65);                // invisível no escuro
color: var(--j-global-primary-color);      // contraste insuficiente no escuro — use --dc-accent
background: var(--dc-dark-surface);        // indefinida no claro
html[data-theme='dark'] .meu-card { ... }  // regra por tela: não escala
:deep(.ant-table-thead > tr > th) { background: #fafafa; }  // vence o ConfigProvider e quebra o escuro
```

## Faltou um tom?

Adicione um token novo em `src/design/dc-tokens.less`, com valor no `:root` **e** o
equivalente no bloco `html[data-theme='dark']`. Não resolva com uma regra
`html[data-theme='dark'] .minha-classe` dentro da tela — isso não escala e é exatamente a
dívida que os tokens vieram pagar.

Contraste mínimo para texto: **4.5:1** sobre a superfície em que ele assenta, nos dois temas.
