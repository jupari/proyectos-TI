# Design System: Seguimiento TI (Estilo HelloGov)

Guía completa de paleta de colores, tipografía, componentes y patrones de interacción para la aplicación Seguimiento TI.

## 1. Paleta de Colores

### Colores Primarios: Teal (Turquesa)

La paleta teal es el color principal de la marca, inspirado en HelloGov. Se utiliza para acciones primarias, botones, links y elementos interactivos.

| Escala | Hex | RGB | Uso |
|--------|-----|-----|-----|
| 50 | `#f0fdfb` | 240, 253, 251 | Fondos muy claros, overlays |
| 100 | `#e0f9f7` | 224, 249, 247 | Fondos claros, estados hover suave |
| 200 | `#ccfbf1` | 204, 251, 241 | Backgrounds alternos, pills suave |
| 300 | `#99f6e4` | 153, 246, 228 | Estados hover, focus rings |
| 400 | `#5eead4` | 94, 234, 212 | Accents, borders |
| **500** | **`#2dd4bf`** | **45, 212, 191** | **Principal: Botones, links, iconos** |
| 600 | `#14b8a6` | 20, 184, 166 | Hover estado botones |
| 700 | `#0d9488` | 13, 148, 136 | Estados activos, focus |
| 800 | `#0f766e` | 15, 118, 110 | Texto oscuro sobre teal claro |
| 900 | `#134e4a` | 19, 78, 74 | Fondos muy oscuros (raro) |

**Uso por componente**:
- **Botones primarios**: bg-teal-500, hover:bg-teal-600, text-white
- **Links**: text-teal-600, hover:text-teal-700, underline-on-hover
- **Inputs focus**: border-teal-500, shadow-focus (anillo teal)
- **Badges de éxito**: bg-teal-100, text-teal-700

### Colores Neutrales: Grises

Utilizados para textos, fondos secundarios y elementos neutros.

| Escala | Hex | RGB | Uso |
|--------|-----|-----|-----|
| 50 | `#f8fafc` | 248, 250, 252 | Fondo de página |
| 100 | `#f1f5f9` | 241, 245, 249 | Fondos suaves |
| 200 | `#e2e8f0` | 226, 232, 240 | Bordes, divisores |
| 300 | `#cbd5e1` | 203, 213, 225 | Hover estados secundarios |
| 400 | `#94a3b8` | 148, 163, 184 | Texto placeholder |
| 500 | `#64748b` | 100, 116, 139 | Texto secundario |
| 600 | `#475569` | 71, 85, 105 | Texto normal |
| 700 | `#334155` | 51, 65, 85 | Texto oscuro |
| 800 | `#1e293b` | 30, 41, 59 | Texto muy oscuro |
| 900 | `#0f172a` | 15, 23, 42 | Fondos muy oscuros |

**Uso por componente**:
- **Texto principal**: text-neutro-700
- **Texto secundario**: text-neutro-600
- **Placeholder**: text-neutro-400
- **Fondos alternativos**: bg-neutro-50
- **Bordes**: border-neutro-200
- **Dividers**: bg-neutro-200

### Colores de Estado: Éxito, Alerta, Peligro

| Estado | Color | Hex | Uso |
|--------|-------|-----|-----|
| **Éxito** | Verde | `#10b981` | Aprobado, completado, activo |
| **Alerta** | Naranja | `#f59e0b` | Atención, pendiente, cautela |
| **Peligro** | Rojo | `#ef4444` | Error, eliminación, crítico |

**Semáforo** (para indicadores visuales):
- Rojo: `#ef4444` (crítico)
- Amarillo: `#f59e0b` (atención)
- Verde: `#10b981` (normal)

**Uso**:
- **Badges de estado**: `<span class="bg-exito/10 text-exito">Aprobado</span>`
- **Botones peligro**: `<button class="bg-peligro hover:bg-peligro-700">Eliminar</button>`
- **Alert boxes**: `border-l-4 border-alerta bg-alerta/10`

## 2. Tipografía

### Familia de Fuentes

Utilizamos **Inter** como familia principal (ya incluida en el proyecto).

```css
font-family: Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica Neue, Arial, sans-serif;
```

**Fallbacks** aseguran que si Inter no carga, usa fuentes del sistema.

### Escala de Tamaños

| Clase | Tamaño | Line Height | Peso | Uso |
|-------|--------|-------------|------|-----|
| `text-xs` | 12px | 1.5 | 400 | Etiquetas pequeñas, metadata |
| `text-sm` | 14px | 1.5 | 400 | Texto de apoyo, hints |
| `text-base` | 16px | 1.5 | 400 | Texto normal de cuerpo |
| `text-lg` | 18px | 1.75 | 500 | Subtítulos |
| `text-xl` | 20px | 1.75 | 600 | Títulos de sección |
| `text-2xl` | 24px | 2 | 700 | Títulos principales |
| `text-3xl` | 30px | 2.25 | 700 | Títulos de página |

### Pesos de Fuente

| Peso | Valor | Uso |
|------|-------|-----|
| Regular | 400 | Texto normal |
| Medium | 500 | Subtítulos, énfasis suave |
| Semibold | 600 | Títulos de subsección |
| Bold | 700 | Títulos principales |

**Ejemplos**:
```html
<!-- Texto normal -->
<p class="text-base text-neutro-700">Descripción normal del proyecto</p>

<!-- Subtítulo -->
<h3 class="text-lg font-semibold text-neutro-800">Nombre del Proyecto</h3>

<!-- Título de página -->
<h1 class="text-3xl font-bold text-neutro-900">Panel Administrativo</h1>
```

## 3. Espaciado

Seguimos un grid de **8px** para consistencia.

| Clase | Píxeles | Uso |
|-------|---------|-----|
| `p-2` | 8px | Padding mínimo |
| `p-3` | 12px | Padding pequeño |
| `p-4` | 16px | Padding normal (inputs, botones) |
| `p-6` | 24px | Padding cards |
| `p-8` | 32px | Padding secciones |
| `gap-2` | 8px | Gap entre items |
| `gap-4` | 16px | Gap normal |
| `gap-6` | 24px | Gap grande |

**Ejemplos**:
```html
<!-- Card con padding generoso -->
<div class="p-6 bg-white rounded-panel shadow-tarjeta">
  <h3 class="text-lg font-semibold mb-4">Título</h3>
  <p class="text-sm text-neutro-600">Contenido</p>
</div>

<!-- Grid de inputs -->
<div class="grid grid-cols-2 gap-4">
  <input type="email" placeholder="Email" />
  <input type="password" placeholder="Contraseña" />
</div>
```

## 4. Componentes Base

### Botón Primario

```html
<button class="
  px-6 py-3
  bg-teal-500 hover:bg-teal-600
  text-white font-medium
  rounded-panel
  transition-colors duration-200
  disabled:opacity-50 disabled:cursor-not-allowed
">
  Acción Primaria
</button>
```

**Variantes**:
- **Primario** (Teal): Acciones principales, alta prioridad
- **Secundario** (Blanco con borde): Acciones alternativas
- **Peligro** (Rojo): Eliminación, descartar
- **Fantasma** (Solo texto): Acciones terciarias

### Input de Texto

```html
<input
  type="text"
  placeholder="Escribe algo..."
  class="
    w-full px-4 py-3
    border-b-2 border-neutro-300
    focus:border-teal-500 focus:outline-none
    text-neutro-700
    transition-colors duration-150
    placeholder:text-neutro-400
  "
/>
```

**Estados**:
- **Normal**: border-neutro-300
- **Focus**: border-teal-500, shadow-focus
- **Error**: border-peligro, text-peligro
- **Disabled**: opacity-50, cursor-not-allowed

### Card

```html
<div class="
  p-6
  bg-white
  rounded-panel
  shadow-tarjeta
  hover:shadow-hover
  transition-shadow duration-200
">
  <h3 class="text-lg font-semibold text-neutro-800 mb-2">Título</h3>
  <p class="text-sm text-neutro-600">Descripción de la card</p>
</div>
```

### Modal / Diálogo

```html
<div class="
  fixed inset-0
  bg-black/50
  flex items-center justify-center
  z-50
">
  <div class="
    bg-white
    rounded-panel
    shadow-hover
    max-w-md w-full
    p-6
    max-h-[90vh] overflow-y-auto
  ">
    <h2 class="text-xl font-bold text-neutro-900 mb-4">Título del Modal</h2>
    <p class="text-neutro-600 mb-6">Contenido del modal</p>
    <div class="flex gap-3 justify-end">
      <button class="px-4 py-2 text-neutro-700 hover:bg-neutro-100 rounded-panel">
        Cancelar
      </button>
      <button class="px-4 py-2 bg-teal-500 text-white hover:bg-teal-600 rounded-panel">
        Confirmar
      </button>
    </div>
  </div>
</div>
```

### Badge / Etiqueta

```html
<!-- Éxito -->
<span class="inline-block px-3 py-1 bg-exito/10 text-exito text-xs font-medium rounded-full">
  Aprobado
</span>

<!-- Alerta -->
<span class="inline-block px-3 py-1 bg-alerta/10 text-alerta text-xs font-medium rounded-full">
  Pendiente
</span>

<!-- Peligro -->
<span class="inline-block px-3 py-1 bg-peligro/10 text-peligro text-xs font-medium rounded-full">
  Error
</span>
```

### Tabla

```html
<table class="w-full border-collapse">
  <thead class="bg-teal-50 border-b-2 border-teal-200">
    <tr>
      <th class="px-4 py-3 text-left text-sm font-semibold text-neutro-700">Columna</th>
      <th class="px-4 py-3 text-left text-sm font-semibold text-neutro-700">Valor</th>
    </tr>
  </thead>
  <tbody>
    <tr class="border-b border-neutro-200 hover:bg-neutro-50 transition-colors">
      <td class="px-4 py-3 text-sm text-neutro-700">Dato 1</td>
      <td class="px-4 py-3 text-sm text-neutro-600">$1.000</td>
    </tr>
  </tbody>
</table>
```

## 5. Sombras

| Clase | Valor | Uso |
|-------|-------|-----|
| `shadow-tarjeta` | 0 1px 3px 0 rgb(0 0 0 / 0.1) | Cards, containers |
| `shadow-hover` | 0 4px 6px -1px rgb(0 0 0 / 0.1) | Hover states, elevated |
| `shadow-focus` | Focus ring teal | Inputs activos |

## 6. Border Radius

| Clase | Píxeles | Uso |
|-------|---------|-----|
| `rounded-panel` | 12px (0.75rem) | Cards, modales, containers |
| `rounded-input` | 8px (0.5rem) | Inputs, botones |
| `rounded-full` | 999px | Pills, badges circulares |

## 7. Transiciones

Usar transiciones suaves para feedback visual:

```css
/* Duración estándar: 150-200ms */
transition-colors duration-150
transition-all duration-200
transition-shadow duration-200
```

**Ejemplos**:
```html
<!-- Botón con transición suave -->
<button class="
  bg-teal-500
  hover:bg-teal-600
  transition-colors duration-200
">
  Hover me
</button>

<!-- Card con elevación en hover -->
<div class="
  shadow-tarjeta
  hover:shadow-hover
  transition-shadow duration-200
">
  Card elevada
</div>
```

## 8. Estados y Accesibilidad

### Estados de Componentes

```html
<!-- Disabled -->
<button disabled class="opacity-50 cursor-not-allowed">
  Botón deshabilitado
</button>

<!-- Loading -->
<button class="opacity-75 cursor-wait">
  <span class="inline-block animate-spin">⏳</span> Cargando...
</button>

<!-- Error -->
<input class="border-peligro bg-peligro/5" />
<p class="text-peligro text-xs mt-1">Este campo es requerido</p>
```

### Focus Visible

Todos los elementos interactivos deben tener un outline visible en focus:

```css
focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-500
```

### Contraste de Color

- **Normal text** (body): 7:1 contrast ratio mínimo (WCAG AAA)
- **Large text** (18pt+): 4.5:1 contrast ratio mínimo
- Verificar contraste con `contrast-checker.com`

## 9. Respuestas Adaptables (Mobile First)

```html
<!-- Stack en mobile, grid en desktop -->
<div class="
  grid grid-cols-1
  md:grid-cols-2
  lg:grid-cols-3
  gap-4
">
  <div>Item 1</div>
  <div>Item 2</div>
  <div>Item 3</div>
</div>
```

**Breakpoints de Tailwind**:
- `sm`: 640px
- `md`: 768px
- `lg`: 1024px
- `xl`: 1280px
- `2xl`: 1536px

## 10. Iconografía

Usar **Material Icons** o similar:

```html
<!-- Material Icon -->
<svg class="w-5 h-5 text-teal-500">
  <use href="#icon-check"></use>
</svg>

<!-- Emoji simple (para MVP) -->
<span class="text-lg">✅</span>
```

**Colores de iconos**:
- Primarios (acciones): `text-teal-500`
- Secondarios: `text-neutro-600`
- Éxito: `text-exito`
- Error: `text-peligro`
- Deshabilitado: `text-neutro-400`

## 11. Ejemplo: Login Card (Fase 2)

```html
<div class="
  min-h-screen
  bg-gradient-to-br from-neutro-50 to-neutro-100
  flex items-center justify-center
  p-4
">
  <div class="
    w-full max-w-md
    bg-white
    rounded-panel
    shadow-hover
    p-8
  ">
    <!-- Logo -->
    <h1 class="text-3xl font-bold text-teal-600 mb-2">Seguimiento TI</h1>
    <p class="text-sm text-neutro-600 mb-6">Sistema de control de proyectos</p>

    <!-- Formulario -->
    <form class="space-y-4">
      <div>
        <label class="block text-sm font-medium text-neutro-700 mb-2">
          Email
        </label>
        <input
          type="email"
          placeholder="tu@email.com"
          class="
            w-full px-4 py-3
            border-b-2 border-neutro-300
            focus:border-teal-500 focus:outline-none
            text-neutro-700
            transition-colors duration-150
            placeholder:text-neutro-400
          "
        />
      </div>

      <div>
        <label class="block text-sm font-medium text-neutro-700 mb-2">
          Contraseña
        </label>
        <input
          type="password"
          placeholder="••••••••"
          class="
            w-full px-4 py-3
            border-b-2 border-neutro-300
            focus:border-teal-500 focus:outline-none
            text-neutro-700
            transition-colors duration-150
            placeholder:text-neutro-400
          "
        />
      </div>

      <div class="text-right">
        <a href="/auth/recuperar" class="text-sm text-teal-600 hover:text-teal-700">
          ¿Olvidó su contraseña?
        </a>
      </div>

      <button class="
        w-full
        py-3
        bg-teal-500 hover:bg-teal-600
        text-white font-medium
        rounded-panel
        transition-colors duration-200
        disabled:opacity-50 disabled:cursor-not-allowed
      ">
        Continuar
      </button>
    </form>
  </div>
</div>
```

## 12. Consideraciones Finales

- **Consistencia**: Usar siempre las clases Tailwind definidas, no valores arbitrarios
- **Accesibilidad**: Testear con lectores de pantalla (NVDA, JAWS, VoiceOver)
- **Performance**: Lazy load images, optimizar animations
- **Responsividad**: Testear en mobile (iPhone, Android), tablet y desktop
- **Contraste**: Verificar ratios de contraste con https://webaim.org/resources/contrastchecker/

---

**Versión**: 1.0 (HelloGov-inspired)
**Última actualización**: 2026-11-16
**Mantener actualizado**: Cambios de colores, componentes nuevos o mejoras documentar aquí

---

## 13. Temas de color y modo claro/oscuro

Los colores salen de variables CSS (`frontend/src/styles.css`) como canales RGB, por lo que Tailwind puede aplicar opacidad (`bg-primario-50/60`).

| Token Tailwind | Uso |
|---|---|
| `primario-50…900` | Escala del color del tema (antes `teal-*`/`marca-*`) |
| `boton`, `boton-hover` | Fondo de botones primarios, switch y selección (siempre con texto blanco) |
| `surface` | Fondo de tarjetas, modales y menús (reemplaza `bg-white`) |
| `neutro-50…900` | Grises; en modo oscuro se invierten |

- **Temas** (atributo `data-tema` en `<html>`): turquesa (por defecto), azul, violeta, rosa, naranja, grafito.
- **Modo** (`data-modo`): `claro`, `oscuro` o `sistema` (sigue `prefers-color-scheme`).
- `TemaService` (`core/tema/tema.service.ts`) aplica y persiste la elección en `localStorage` (`sp_tema`, `sp_modo`); un script en `index.html` la aplica antes de pintar para evitar parpadeos.
- Selector de usuario: icono de paleta en la barra superior (`layout/topbar/selector-tema`).
- En modo oscuro la escala `primario` se reasigna: 50–200 son tintes oscuros y 600–900 son tonos claros, de modo que `text-primario-800` sea siempre legible sobre `bg-primario-50`.
- No usar `text-primario-*` o `bg-primario-700` como fondo de botón con texto blanco: usar `bg-boton`.
- **Gráficos (Chart.js)** no heredan CSS: pasar una función `() => colorTema('primario-400')` como color del dataset; `app-grafico` se redibuja al cambiar de tema.
- Para añadir un tema: agregar un bloque `[data-tema="x"]` y su variante `[data-modo="oscuro"][data-tema="x"]` en `styles.css` y una entrada en `TEMAS`.
