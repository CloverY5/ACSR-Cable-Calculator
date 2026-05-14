# Calculadora de Líneas de Transmisión ACSR

Aplicación de escritorio (Python + Tkinter) para el cálculo de los parámetros eléctricos de líneas de transmisión aéreas con conductores ACSR (Aluminum Conductor Steel Reinforced). Desarrollada como parte del laboratorio de la asignatura **Análisis de Sistemas Eléctricos de Potencia (ASEP)** — 8° semestre, Ingeniería Eléctrica.

---

## Características principales

- **Catálogo integrado** de conductores ACSR estándar (Swan, Sparrow, Drake, Hawk, Dove, etc.) basado en la tabla de CENTELSA, con búsqueda directa por código o filtrado en cascada (calibre → cableado → conductor).
- **Corrección rigurosa de resistencia por temperatura** específica para ACSR, considerando aluminio y acero como conductores en paralelo, cada uno con su propia resistividad, área y coeficiente térmico.
- **Tres configuraciones de línea** soportadas:
  - Línea trifásica transpuesta (simétrica o asimétrica)
  - Línea trifásica no transpuesta (resultados por fase)
  - Línea de doble circuito
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
│   └── main_view.py               ← Interfaz gráfica Tkinter
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

Aparecerá la ventana principal. El flujo de uso es:

1. Seleccionar un conductor del catálogo (Método 1 o Método 2).
2. Confirmar el conductor con el botón **Confirmar Conductor**.
3. Seleccionar la configuración de la línea: transpuesta, no transpuesta o doble circuito.
4. Ingresar los parámetros eléctricos y geométricos (frecuencia, longitud, temperatura, distancias entre fases, etc.).
5. Hacer clic en **CALCULAR PARÁMETROS** para obtener los resultados.

---

## Metodología de cálculo

### 1. Corrección de resistencia por temperatura (ACSR)

A diferencia de la fórmula simplificada para aluminio puro, esta calculadora aplica el procedimiento riguroso para conductores ACSR, que considera al cable como dos resistencias en paralelo: el núcleo de acero y la corona de hilos de aluminio.

**Paso 1 — Área de cada material:**

$$A = n_h \cdot \frac{\pi}{4} \cdot D^2 \quad [\text{mm}^2]$$

donde `n_h` es el número de hilos y `D` su diámetro individual.

**Paso 2 — Resistencia DC a 20 °C de cada material, con factor de cableado:**

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

**Doble circuito** — RMG equivalente del grupo paralelo:

$$\text{RMG}_{eq} = \sqrt{\text{RMG} \cdot D_{\text{entre}}}$$

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

Las fórmulas del bundle son las mismas pero usando `r` en lugar de `r'`.

### 4. Reactancias

$$X_L = 2 \pi f L \cdot 1000 \quad [\Omega/\text{km}]$$

$$X_c = \frac{1}{2 \pi f C \cdot 1000} \quad [\Omega \cdot \text{km}]$$

**Totales de línea:**

- `R_total = R · L` (resistencia en serie)
- `X_L,total = X_L · L` (reactancia inductiva en serie)
- `X_c,total = X_c / L` (reactancia capacitiva en derivación)

---

## Interfaz gráfica

La ventana se organiza en cuatro secciones principales:

1. **Catálogo ACSR** — Selección del conductor por código directo o por filtros en cascada.
2. **Parámetros de la línea** — Configuración geométrica y eléctrica.
3. **Botón CALCULAR PARÁMETROS** — Ejecuta los cálculos según la configuración seleccionada.
4. **Resultados** — Organizados en tres bloques diferenciados:
   - ① Corrección de Resistencia por Temperatura (ACSR) — Tabla paso a paso por material
   - ② Inductancia y Reactancia Inductiva
   - ③ Capacitancia y Reactancia Capacitiva
   - ④ Parámetros por fase (visible solo en líneas no transpuestas)

---

## Validación

El módulo de cálculo de resistencia se validó contra el ejemplo de referencia del **conductor Dove (26/7) a 75 °C** del documento *Corrección de resistencia por temperatura para ACSR*:

| Resultado | Esperado | Calculado |
|---|---|---|
| Área Al | 282.585 mm² | 282.585 mm² |
| Área Ac | 45.918 mm² | 45.918 mm² |
| R₂₀ Al | 0.101365 Ω/km | 0.101365 Ω/km |
| R₂₀ Ac | 3.11366 Ω/km | 3.11366 Ω/km |
| R(75°C) Al | 0.12381 Ω/km | 0.123816 Ω/km |
| R(75°C) Ac | 3.8509 Ω/km | 3.850901 Ω/km |
| **R_TOT** | **0.119953 Ω/km** | **0.119959 Ω/km** |

Las diferencias mínimas (sexto decimal) corresponden al redondeo intermedio en el documento de referencia.

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