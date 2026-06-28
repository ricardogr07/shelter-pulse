export type Locale = 'en' | 'es';
export const locales: Locale[] = ['en', 'es'];
export const defaultLocale: Locale = 'en';

export interface Dict {
  nav: { home: string; demo: string; howItWorks: string; buildCustom: string };
  landing: { title: string; subtitle: string; ctaDemo: string; ctaCustom: string; feat1Title: string; feat1Desc: string; feat2Title: string; feat2Desc: string; feat3Title: string; feat3Desc: string; footer1: string; footer2: string };
  demo: { configTitle: string; housingCap: string; isoSlots: string; fosterPlaces: string; kittenSurge: string; budget: string; btnBaseline: string; baselineTitle: string; baselineDesc: string; overflow: string; budgetUsed: string; bottleneckTitle: string; isoDesc: string; throughputDesc: string; btnOptimize: string; optTitle: string; optDesc: string; reduction: string; compareTitle: string; strategy: string; exportTitle: string; exportDesc: string; btnDownload: string; btnApi: string };
  howItWorks: { title: string; subtitle: string; s1Title: string; s1: string; s2Title: string; s2Intro: string; s2Flow: string; s2Items: string[]; s2Note: string; s3Title: string; s3Intro: string; s3Items: string[]; s3Warning: string; s4Title: string; s4Intro: string; s4Steps: string[]; s4Note: string; s5Title: string; s5Intro: string; s5Stats: string[]; s5Without: string; s5With: string; s6Title: string; s6: string };
  simulate: { title: string; subtitle: string; labels: Record<string, string>; tooltips: Record<string, string>; btnSimulate: string; btnOptimize: string; resultTitle: string; optResultTitle: string; overflow: string; cost: string; feasible: string; analytics?: { timeline: string; sensitivity: string } };
  common: { loading: string; error: string; yes: string; no: string };
}

const en: Dict = {
  nav: { home: "Home", demo: "Demo", howItWorks: "How It Works", buildCustom: "Build Custom" },
  landing: {
    title: "Simulate your shelter.\nOptimize your budget.",
    subtitle: "Kitten season overwhelms shelters every spring. ShelterPulse simulates your capacity under uncertainty and finds the best way to spend your intervention budget \u2014 before a single cat is at risk.",
    ctaDemo: "Try the Demo \u2192", ctaCustom: "Build Custom Scenario \u2192",
    feat1Title: "Discrete-Event Simulation", feat1Desc: "SimPy-powered model of the full cat lifecycle \u2014 intake surges, isolation queues, medical clearance, foster, and adoption.",
    feat2Title: "Bayesian Optimization", feat2Desc: "Finds the best budget allocation across foster support, clinic hours, isolation expansion, and adoption events.",
    feat3Title: "Custom Scenarios", feat3Desc: "Configure your own shelter \u2014 geography, climate, size, and budget \u2014 and simulate against your specific constraints.",
    footer1: "ShelterPulse \u00b7 Open-source simulation lab for cat shelter resource allocation",
    footer2: "Built for #hackthekitty 2026",
  },
  demo: {
    configTitle: "Shelter Configuration", housingCap: "Housing Capacity", isoSlots: "Isolation Slots", fosterPlaces: "Foster Places", kittenSurge: "Kitten Surge Multiplier", budget: "Intervention Budget",
    btnBaseline: "Run Baseline", baselineTitle: "Baseline Results", baselineDesc: "How your shelter performs with no interventions during kitten season.",
    overflow: "Overflow Cat-Days", budgetUsed: "Budget Used",
    bottleneckTitle: "Bottleneck Analysis", isoDesc: "Isolation queue is the primary constraint.", throughputDesc: "Adoption throughput limits outflow.",
    btnOptimize: "Optimize Budget", optTitle: "Optimized Allocation", optDesc: "Best budget split found by Bayesian optimization.", reduction: "Overflow Reduction",
    compareTitle: "Baseline vs. Optimized", strategy: "Strategy",
    exportTitle: "Export Results", exportDesc: "Download full results or access via API.", btnDownload: "Download CSV", btnApi: "View API Docs",
  },
  howItWorks: {
    title: "How It Works", subtitle: "From intake to adoption \u2014 a discrete-event simulation of your shelter.",
    s1Title: "The Problem", s1: "Every spring, kitten season floods shelters with more cats than they can house. Without planning, shelters hit capacity, leading to longer stays, stressed cats, and difficult decisions.",
    s2Title: "The Cat Flow", s2Intro: "Each cat moves through a realistic lifecycle:", s2Flow: "Intake \u2192 Assessment \u2192 Isolation/Medical \u2192 Housing \u2192 Foster \u2192 Adoption",
    s2Items: ["Intake follows a non-homogeneous Poisson process (seasonal surges)", "Kittens require extra neonatal care and longer isolation", "Medical clearance depends on vet tech availability", "Foster relieves housing pressure but requires coordination"],
    s2Note: "Each stage has stochastic durations drawn from real shelter data distributions.",
    s3Title: "Resources & Constraints", s3Intro: "Your shelter has finite resources:",
    s3Items: ["Housing slots (cages + community rooms)", "Isolation slots (URI, ringworm quarantine)", "Vet tech FTE (medical clearance bottleneck)", "Foster network capacity"],
    s3Warning: "When resources are full, cats queue \u2014 that\u2019s overflow.",
    s4Title: "Optimization", s4Intro: "Given a fixed budget, ShelterPulse finds the best allocation across 4 interventions:",
    s4Steps: ["Foster support (stipends, supplies)", "Extra clinic hours (more vet tech time)", "Temporary isolation expansion", "Adoption events (marketing, fee waivers)"],
    s4Note: "Bayesian optimization with common random numbers ensures fair comparison between candidates.",
    s5Title: "Results", s5Intro: "The optimizer compares your baseline against the best allocation:",
    s5Stats: ["Overflow cat-days (primary metric)", "Peak occupancy", "Average length of stay", "Adoption throughput"],
    s5Without: "Without optimization: reactive, over-capacity, stressed.", s5With: "With optimization: proactive, within capacity, humane.",
    s6Title: "Try It", s6: "Run the demo with Whisker Haven or build your own scenario with custom parameters.",
  },
  simulate: {
    title: "Custom Simulation", subtitle: "Configure your shelter and run a simulation tailored to your constraints.",
    labels: { name: "Scenario Name", duration_days: "Duration (days)", housing_capacity: "Housing Capacity", isolation_slots: "Isolation Slots", vet_tech_fte: "Vet Tech FTE", intervention_budget: "Intervention Budget ($)", mean_intake_per_day: "Mean Intake/Day", kitten_fraction: "Kitten Fraction", base_adoption_rate: "Base Adoption Rate" },
    tooltips: { name: "A label for this scenario. Doesn't affect simulation.", duration_days: "How many days to simulate. 90 covers a full kitten season.", housing_capacity: "Total cages + community rooms for cats in general population.", isolation_slots: "Dedicated slots for cats requiring medical isolation (URI, ringworm).", vet_tech_fte: "Full-time equivalent vet techs. 1.0 = one tech working 8hr/day.", intervention_budget: "Fixed budget to split across 4 strategies. Cannot be exceeded.", mean_intake_per_day: "Average new cats arriving per day (before seasonal surge).", kitten_fraction: "Fraction of intake that are kittens (<6 months). More kittens = more neonatal care.", base_adoption_rate: "Baseline daily adoption probability for adoption-ready cats." },
    btnSimulate: "Run Simulation", btnOptimize: "Optimize", resultTitle: "Simulation Results", optResultTitle: "Optimization Results", overflow: "Overflow Cat-Days", cost: "Intervention Budget", feasible: "Feasible", analytics: { timeline: "Timeline", sensitivity: "Sensitivity" },
  },
  common: { loading: "Loading\u2026", error: "Something went wrong. Please try again.", yes: "Yes", no: "No" },
};

const es: Dict = {
  nav: { home: "Inicio", demo: "Demo", howItWorks: "C\u00f3mo Funciona", buildCustom: "Crear Escenario" },
  landing: {
    title: "Simula tu refugio.\nOptimiza tu presupuesto.",
    subtitle: "La temporada de gatitos satura los refugios cada primavera. ShelterPulse simula tu capacidad bajo incertidumbre y encuentra la mejor forma de gastar tu presupuesto de intervenci\u00f3n \u2014 antes de que un solo gato est\u00e9 en riesgo.",
    ctaDemo: "Probar el Demo \u2192", ctaCustom: "Crear Escenario Personalizado \u2192",
    feat1Title: "Simulaci\u00f3n de Eventos Discretos", feat1Desc: "Modelo del ciclo de vida completo del gato con SimPy \u2014 oleadas de ingreso, colas de aislamiento, alta m\u00e9dica, hogar temporal y adopci\u00f3n.",
    feat2Title: "Optimizaci\u00f3n Bayesiana", feat2Desc: "Encuentra la mejor asignaci\u00f3n de presupuesto entre apoyo a hogares temporales, horas de cl\u00ednica, expansi\u00f3n de aislamiento y eventos de adopci\u00f3n.",
    feat3Title: "Escenarios Personalizados", feat3Desc: "Configura tu propio refugio \u2014 geograf\u00eda, clima, tama\u00f1o y presupuesto \u2014 y simula con tus restricciones espec\u00edficas.",
    footer1: "ShelterPulse \u00b7 Laboratorio de simulaci\u00f3n de c\u00f3digo abierto para asignaci\u00f3n de recursos en refugios de gatos",
    footer2: "Creado para #hackthekitty 2026",
  },
  demo: {
    configTitle: "Configuraci\u00f3n del Refugio", housingCap: "Capacidad de Alojamiento", isoSlots: "Espacios de Aislamiento", fosterPlaces: "Hogares Temporales", kittenSurge: "Multiplicador de Temporada", budget: "Presupuesto de Intervenci\u00f3n",
    btnBaseline: "Ejecutar L\u00ednea Base", baselineTitle: "Resultados Base", baselineDesc: "C\u00f3mo funciona tu refugio sin intervenciones durante la temporada de gatitos.",
    overflow: "D\u00edas-Gato en Exceso", budgetUsed: "Presupuesto Usado",
    bottleneckTitle: "An\u00e1lisis de Cuellos de Botella", isoDesc: "La cola de aislamiento es la restricci\u00f3n principal.", throughputDesc: "El flujo de adopciones limita las salidas.",
    btnOptimize: "Optimizar Presupuesto", optTitle: "Asignaci\u00f3n Optimizada", optDesc: "Mejor distribuci\u00f3n de presupuesto encontrada por optimizaci\u00f3n bayesiana.", reduction: "Reducci\u00f3n de Exceso",
    compareTitle: "Base vs. Optimizado", strategy: "Estrategia",
    exportTitle: "Exportar Resultados", exportDesc: "Descarga resultados completos o accede v\u00eda API.", btnDownload: "Descargar CSV", btnApi: "Ver Docs de API",
  },
  howItWorks: {
    title: "C\u00f3mo Funciona", subtitle: "Del ingreso a la adopci\u00f3n \u2014 simulaci\u00f3n de eventos discretos de tu refugio.",
    s1Title: "El Problema", s1: "Cada primavera, la temporada de gatitos inunda los refugios con m\u00e1s gatos de los que pueden alojar. Sin planeaci\u00f3n, se alcanza la capacidad m\u00e1xima, generando estancias m\u00e1s largas, gatos estresados y decisiones dif\u00edciles.",
    s2Title: "El Flujo del Gato", s2Intro: "Cada gato pasa por un ciclo de vida realista:", s2Flow: "Ingreso \u2192 Evaluaci\u00f3n \u2192 Aislamiento/M\u00e9dico \u2192 Alojamiento \u2192 Hogar Temporal \u2192 Adopci\u00f3n",
    s2Items: ["El ingreso sigue un proceso de Poisson no homog\u00e9neo (oleadas estacionales)", "Los gatitos requieren cuidado neonatal extra y aislamiento m\u00e1s largo", "El alta m\u00e9dica depende de la disponibilidad de t\u00e9cnicos veterinarios", "Los hogares temporales alivian la presi\u00f3n pero requieren coordinaci\u00f3n"],
    s2Note: "Cada etapa tiene duraciones estoc\u00e1sticas basadas en distribuciones de datos reales.",
    s3Title: "Recursos y Restricciones", s3Intro: "Tu refugio tiene recursos finitos:",
    s3Items: ["Espacios de alojamiento (jaulas + salas comunitarias)", "Espacios de aislamiento (cuarentena por URI, ti\u00f1a)", "T\u00e9cnicos veterinarios FTE (cuello de botella m\u00e9dico)", "Capacidad de la red de hogares temporales"],
    s3Warning: "Cuando los recursos se saturan, los gatos hacen cola \u2014 eso es el exceso.",
    s4Title: "Optimizaci\u00f3n", s4Intro: "Con un presupuesto fijo, ShelterPulse encuentra la mejor asignaci\u00f3n entre 4 intervenciones:",
    s4Steps: ["Apoyo a hogares temporales (subsidios, suministros)", "Horas cl\u00ednicas extra (m\u00e1s tiempo de t\u00e9cnicos)", "Expansi\u00f3n temporal de aislamiento", "Eventos de adopci\u00f3n (marketing, exenci\u00f3n de cuotas)"],
    s4Note: "La optimizaci\u00f3n bayesiana con n\u00fameros aleatorios comunes garantiza comparaciones justas.",
    s5Title: "Resultados", s5Intro: "El optimizador compara tu l\u00ednea base contra la mejor asignaci\u00f3n:",
    s5Stats: ["D\u00edas-gato en exceso (m\u00e9trica principal)", "Ocupaci\u00f3n m\u00e1xima", "Estancia promedio", "Flujo de adopciones"],
    s5Without: "Sin optimizaci\u00f3n: reactivo, sobrecapacidad, estresante.", s5With: "Con optimizaci\u00f3n: proactivo, dentro de capacidad, humano.",
    s6Title: "Pru\u00e9balo", s6: "Ejecuta el demo con Whisker Haven o crea tu propio escenario con par\u00e1metros personalizados.",
  },
  simulate: {
    title: "Simulaci\u00f3n Personalizada", subtitle: "Configura tu refugio y ejecuta una simulaci\u00f3n adaptada a tus restricciones.",
    labels: { name: "Nombre del Escenario", duration_days: "Duraci\u00f3n (d\u00edas)", housing_capacity: "Capacidad de Alojamiento", isolation_slots: "Espacios de Aislamiento", vet_tech_fte: "T\u00e9cnicos Vet. FTE", intervention_budget: "Presupuesto ($)", mean_intake_per_day: "Ingreso Promedio/D\u00eda", kitten_fraction: "Fracci\u00f3n de Gatitos", base_adoption_rate: "Tasa Base de Adopci\u00f3n" },
    tooltips: { name: "Etiqueta para este escenario. No afecta la simulaci\u00f3n.", duration_days: "Cu\u00e1ntos d\u00edas simular. 90 cubre una temporada completa de gatitos.", housing_capacity: "Total de jaulas + salas comunitarias para gatos en poblaci\u00f3n general.", isolation_slots: "Espacios dedicados para gatos que requieren aislamiento m\u00e9dico (URI, ti\u00f1a).", vet_tech_fte: "T\u00e9cnicos veterinarios equivalentes a tiempo completo. 1.0 = un t\u00e9cnico 8hrs/d\u00eda.", intervention_budget: "Presupuesto fijo a dividir entre 4 estrategias. No se puede exceder.", mean_intake_per_day: "Promedio de gatos nuevos por d\u00eda (antes de la oleada estacional).", kitten_fraction: "Fracci\u00f3n del ingreso que son gatitos (<6 meses). M\u00e1s gatitos = m\u00e1s cuidado neonatal.", base_adoption_rate: "Probabilidad diaria base de adopci\u00f3n para gatos listos." },
    btnSimulate: "Ejecutar Simulaci\u00f3n", btnOptimize: "Optimizar", resultTitle: "Resultados de Simulaci\u00f3n", optResultTitle: "Resultados de Optimizaci\u00f3n", overflow: "D\u00edas-Gato en Exceso", cost: "Presupuesto", feasible: "Factible", analytics: { timeline: "L\u00ednea de tiempo", sensitivity: "Sensibilidad" },
  },
  common: { loading: "Cargando\u2026", error: "Algo sali\u00f3 mal. Intenta de nuevo.", yes: "S\u00ed", no: "No" },
};

const dictionaries: Record<Locale, Dict> = { en, es };

export function getDictionary(locale: string): Dict {
  return dictionaries[locale as Locale] ?? dictionaries.en;
}
