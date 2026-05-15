# Calculadora de Líneas de Transmisión ACSR

Aplicación de escritorio (Python + Tkinter) para el cálculo de los parámetros eléctricos de líneas de transmisión aéreas con conductores ACSR (Aluminum Conductor Steel Reinforced) y conductores sólidos. Desarrollada como parte del laboratorio de la asignatura **Análisis de Sistemas Eléctricos de Potencia (ASEP)** — 8° semestre, Ingeniería Eléctrica.

---

## Características principales

- **Catálogo integrado** de conductores ACSR estándar (Swan, Sparrow, Drake, Hawk, Dove, etc.) basado en la tabla de CENTELSA, con búsqueda directa por código o filtrado en cascada (calibre → cableado → conductor).
- **Corrección rigurosa de resistencia por temperatura** específica para ACSR, considerando aluminio y acero como conductores en paralelo, cada uno con su propia resistividad, área y coeficiente térmico.
- **Cuatro configuraciones de línea** soportadas:
  - Línea trifásica transpuesta (simétrica o asimétrica)
  - Línea trifásica no transpuesta (resultados individuales por fase)
  - Doble circuito / conductores en paralelo con **conductores iguales**
  - Doble circuito / conductores en paralelo con **conductores distintos** entre circuitos
- **Geometría flexible para doble circuito**: ingreso por coordenadas (x, y) de cada conductor, permitiendo número arbitrario de conductores por lado (2, 3, 4 o más) y disposiciones irregulares.
- **Soporte para conductores sólidos** (cobre u otro material) además del catálogo ACSR, mediante ingreso manual del radio.
- **Haces de 1 a 4 conductores por fase** con cálculo automático del RMG y radio equivalentes.
- **Cálculo completo de inductancia y capacitancia** con sus respectivas reactancias y totales de línea.

---

## Estructura del proyecto

```
ACSR-Calculator/
├── main.py                        ← Punto de entrada
├── requirements.txt               ← Dependencias
├── ACSR-Tabla-RMG.csv             ← Catálogo de conductores
├── model/
│   ├── __init__.py
│   ├── conductor_db.py            ← Carga y consulta del catálogo
│   └── calculations.py            ← Motor de cálculo (resistencia, L, C)
├── view/
│   ├── __init__.py
│   └── main_view.py               ← Interfaz gráfica Tkinter + diálogo doble circuito
└── controller/
    ├── __init__.py
    └── app_controller.py          ← Orquestación View ↔ Model
```

El proyecto sigue el patrón **MVC** (Model-View-Controller) para mantener separadas la lógica de datos, la interfaz y la coordinación entre ambas.

---

## Requisitos

- Python 3.10 o superior (recomendado 3.12)
- Tkinter (incluido en la instalación estándar de Python en Windows)
- pandas ≥ 1.5.0

Instalación de dependencias:

```bash
pip install -r requirements.txt
```

---

## Cómo ejecutar

Desde la carpeta raíz del proyecto:

```bash
python main.py
```

### Flujo general de uso

1. Seleccionar un conductor del catálogo (Método 1 directo o Método 2 en cascada).
2. Confirmar el conductor con el botón **Confirmar Conductor**.
3. Seleccionar la configuración de la línea: transpuesta, no transpuesta o doble circuito.
4. Ingresar los parámetros eléctricos generales (frecuencia, longitud, temperatura).
5. Según la configuración:
   - **Transpuesta / No Transpuesta**: ingresar distancias entre fases `D₁₂`, `D₂₃`, `D₃₁` y, si aplica, número de conductores por fase y separación del haz.
   - **Doble Circuito**: hacer clic en `⚙ Configurar Doble Circuito` para abrir el diálogo de configuración (ver siguiente sección).
6. Hacer clic en **CALCULAR PARÁMETROS** para obtener los resultados.

### Configuración del Doble Circuito

El botón **⚙ Configurar Doble Circuito** abre un diálogo modal donde se especifica:

**Tipo de conductores**: un checkbox `Mismo conductor en ambos circuitos`:
- Marcado → ambos lados usan el conductor principal seleccionado en el catálogo.
- Desmarcado → se habilita el lado B para elegir otro conductor distinto.

**Lado A (Circuito 1)**:
- *ACSR*: utiliza el conductor principal ya confirmado.
- *Sólido*: pide el radio en milímetros (para cobre o conductores sin catálogo).

**Lado B (Circuito 2)** — solo si los conductores son distintos:
- *ACSR*: selector independiente del catálogo (calibre → cableado → conductor → confirmar).
- *Sólido*: radio en milímetros.

**Coordenadas (x, y)** de cada conductor en metros:
- Una tabla editable para cada lado.
- Botones `+ Agregar` y `− Quitar` permiten ajustar el número de conductores por lado (2, 3, 4 o los que se necesiten).
- El origen es arbitrario; solo importan las distancias relativas.

Al hacer clic en `Aceptar`, la configuración queda guardada. Se puede modificar en cualquier momento abriendo el diálogo nuevamente.

---

## Metodología de cálculo

### 1. Corrección de resistencia por temperatura (ACSR)

Procedimiento riguroso que considera al cable como dos resistencias en paralelo: el núcleo de acero y la corona de hilos de aluminio.

**Paso 1 — Área de cada material:**

$$A = n_h \cdot \frac{\pi}{4} \cdot D^2 \quad [\text{mm}^2]$$

**Paso 2 — Resistencia DC a 20 °C de cada material:**

$$R_{20} = \frac{\rho \cdot 1000 \cdot \text{Factor}}{A} \quad [\Omega/\text{km}]$$

| Material | ρ (Ω·mm²/m) | α₁ (1/°C) |
|---|---|---|
| Aluminio | 0.02781 | 0.004027 |
| Acero | 0.14017 | 0.004305 |

| Hilos | Factor |
|---|---|
| ≤ 3 | ×1.01 |
| 4–11 | ×1.02 |
| > 11 | ×1.03 |

**Paso 3 — Corrección lineal a la temperatura final:**

$$R_T = R_{20} \cdot [1 + \alpha_1 (T_2 - T_1)]$$

con `T₁ = 20 °C` y `α₁` correspondiente al material.

**Paso 4 — Combinación en paralelo:**

$$R_{\text{TOT}} = \frac{R_{Al} \cdot R_{Ac}}{R_{Al} + R_{Ac}} \quad [\Omega/\text{km}]$$

### 2. Inductancia

**Línea transpuesta** (simétrica o asimétrica):

$$L = 2 \times 10^{-7} \cdot \ln\left(\frac{\text{DMG}}{\text{RMG}_{\text{haz}}}\right) \quad [\text{H/m}]$$

donde `DMG = ∛(D₁₂·D₂₃·D₃₁)`.

**Línea no transpuesta** — inductancia diferente por fase:

$$L_a = 2 \times 10^{-7} \cdot \ln\left(\frac{\sqrt{D_{12} \cdot D_{31}}}{r'}\right)$$

$$L_b = 2 \times 10^{-7} \cdot \ln\left(\frac{\sqrt{D_{12} \cdot D_{23}}}{r'}\right)$$

$$L_c = 2 \times 10^{-7} \cdot \ln\left(\frac{\sqrt{D_{23} \cdot D_{31}}}{r'}\right)$$

**Doble circuito / conductores en paralelo:**

El RMG de cada lado (lado A con `n` conductores, lado B con `m` conductores) se calcula a partir de las coordenadas (x, y) usando la fórmula general:

$$\text{RMG} = \sqrt[n^2]{\prod_{i=1}^{n} \prod_{j=1}^{n} D_{ij}}$$

donde `D_ii` se reemplaza por el GMR del conductor individual (RMG de tabla para ACSR, `r · 0.7788` para conductores sólidos).

La DMG mutua entre los dos lados se calcula como:

$$\text{DMG} = \sqrt[m \cdot n]{\prod_{i \in A} \prod_{j \in B} D_{ij}}$$

donde `D_ij` es la distancia euclidiana entre coordenadas.

La inductancia final depende del tipo de conductores:

- **Conductores iguales** (mismo conductor en ambos lados):

$$L = 4 \times 10^{-7} \cdot \ln\left(\frac{\text{DMG}}{\text{RMG}}\right) \quad [\text{H/m}]$$

- **Conductores distintos**:

$$L_A = 2 \times 10^{-7} \cdot \ln\left(\frac{\text{DMG}}{\text{RMG}_A}\right), \quad L_B = 2 \times 10^{-7} \cdot \ln\left(\frac{\text{DMG}}{\text{RMG}_B}\right)$$

$$L_T = L_A + L_B \quad [\text{H/m}]$$

**RMG del haz** para `n` conductores por fase con separación `d`:

| n | RMG_haz |
|---|---|
| 1 | `r'` |
| 2 | `√(r'·d)` |
| 3 | `∛(r'·d²)` |
| 4 | `1.09·⁴√(r'·d³)` |

### 3. Capacitancia

Análoga a la inductancia pero usando el **radio físico** del conductor en lugar del RMG:

$$C = \frac{2 \pi \varepsilon_0}{\ln(\text{DMG} / r_{eq})} \quad [\text{F/m}]$$

con `ε₀ = 8.85 × 10⁻¹² F/m`.

Para doble circuito con conductores iguales:

$$C = \frac{4 \pi \varepsilon_0}{\ln(\text{DMG} / r)} \quad [\text{F/m}]$$

Para doble circuito con conductores distintos se calcula `C_A` y `C_B` y se combinan en paralelo.

### 4. Reactancias

$$X_L = 2 \pi f L \cdot 1000 \quad [\Omega/\text{km}]$$

$$X_c = \frac{1}{2 \pi f C \cdot 1000} \quad [\Omega \cdot \text{km}]$$

**Totales de línea:**

- `R_total = R · L` (resistencia en serie)
- `X_L,total = X_L · L` (reactancia inductiva en serie)
- `X_c,total = X_c / L` (reactancia capacitiva en derivación)

---

## Interfaz gráfica

La ventana principal se organiza en cuatro bloques verticales:

1. **Catálogo ACSR — Conductor principal (Circuito A)** — Selección por código directo o por filtros en cascada.
2. **Parámetros de la Línea** — Configuración, frecuencia, longitud, temperatura. Para líneas de un solo circuito incluye conductores por fase y distancias `D₁₂/D₂₃/D₃₁`. Para doble circuito muestra el botón de configuración.
3. **Botón CALCULAR PARÁMETROS** — Ejecuta los cálculos según la configuración seleccionada.
4. **Resultados** — Organizados en hasta cinco secciones:
   - ① Corrección de Resistencia por Temperatura (ACSR) — Tabla paso a paso por material
   - ② Inductancia y Reactancia Inductiva
   - ③ Capacitancia y Reactancia Capacitiva
   - ④ Parámetros por fase (visible solo en líneas no transpuestas)
   - ⑤ Detalle de Doble Circuito (visible solo en doble circuito): muestra el conductor de cada lado, número de conductores, RMG por lado, L y C por lado (cuando conductores son distintos), DMG entre lados y tipo (iguales/distintos)

---

## Validación

### Corrección de resistencia ACSR

Validado contra el ejemplo de referencia del **conductor Dove (26/7) a 75 °C**:

| Resultado | Esperado | Calculado |
|---|---|---|
| Área Al | 282.585 mm² | 282.585 mm² |
| Área Ac | 45.918 mm² | 45.918 mm² |
| R₂₀ Al | 0.101365 Ω/km | 0.101365 Ω/km |
| R₂₀ Ac | 3.11366 Ω/km | 3.11366 Ω/km |
| R(75°C) Al | 0.12381 Ω/km | 0.123816 Ω/km |
| R(75°C) Ac | 3.8509 Ω/km | 3.850901 Ω/km |
| **R_TOT** | **0.119953 Ω/km** | **0.119959 Ω/km** |

### Doble circuito (geometría 3+2 conductores)

Validado contra el ejemplo de la figura 2.9 del libro de referencia:
- Lado A: 3 conductores en columna `x=0`, alturas `y={8, 4, 0}` m
- Lado B: 2 conductores en columna `x=8`, alturas `y={6, 2}` m
- Conductor sólido de radio `r=50 mm`

| Resultado | Valor calculado |
|---|---|
| RMG Lado A (3 cond.) | 0.9963 m |
| RMG Lado B (2 cond.) | 0.3947 m |
| DMG entre lados | 8.7937 m |
| L total (iguales) | 0.8711 mH/km |

Las diferencias mínimas (sexto decimal) corresponden al redondeo intermedio en los documentos de referencia.

---

## Catálogo de conductores

El archivo `ACSR-Tabla-RMG.csv` contiene los siguientes campos para cada conductor:

| Columna | Descripción |
|---|---|
| Cableado (Al/Ac) | Relación de hilos aluminio/acero (ej. 26/7) |
| Código | Nombre comercial del conductor (Drake, Hawk, Dove, etc.) |
| Calibre (AWG/Kcmil) | Calibre en AWG o miles de circular mils |
| D. Alambre Acero (mm) | Diámetro de cada hilo de acero |
| D. Alambre Al (mm) | Diámetro de cada hilo de aluminio |
| D. Núcleo (mm) | Diámetro del núcleo de acero |
| D. Total (mm) | Diámetro total del conductor |
| RMG (mm) | Radio medio geométrico |
| Peso Al/Acero/Total (kg/km) | Pesos por kilómetro |
| Carga de Rotura (kg-f) | Carga de rotura mecánica |
| R. Elec. CD a 20°C (Ω/km) | Resistencia DC a 20 °C (de fábrica) |
| R. Elec. CA a 75°C (Ω/km) | Resistencia AC a 75 °C |
| Capacidad In (A) | Corriente nominal |
| Capacidad Icc (kA) | Corriente de cortocircuito |

---

## Referencias

- Stevenson, W. D. (1996). *Análisis de sistemas eléctricos de potencia*.
- Glover, J. D., Sarma, M. S., & Overbye, T. J. (2017). *Power System Analysis and Design*.
- CENTELSA — Catálogo técnico de conductores eléctricos.
- IEEE Std 738-2012 — Standard for Calculating the Current-Temperature of Bare Overhead Conductors.

---

## Tecnologías

- **Python 3.12** — Lenguaje base
- **Tkinter / ttk** — Interfaz gráfica nativa
- **pandas** — Lectura y manipulación del catálogo CSV
- **Arquitectura MVC** — Separación entre modelo, vista y controlador

---

## Licencia

Proyecto académico de uso libre con fines educativos.

---

## Autores

Desarrollado como parte de las prácticas de laboratorio de Análisis de Sistemas Eléctricos de Potencia (ASEP) por:

- **Clover Y5**
- **H. R. Roger Takeshi**
- **E. S. Genesis Abril**
- **R. H. Marco Antonio**
