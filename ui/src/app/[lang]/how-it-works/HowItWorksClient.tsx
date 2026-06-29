'use client';
import { useState, useRef, useEffect } from 'react';
import Link from 'next/link';
import { getDictionary } from '@/i18n/dictionaries';
import katex from 'katex';
import 'katex/dist/katex.min.css';

function Tex({ children, display = false }: { children: string; display?: boolean }) {
  const ref = useRef<HTMLSpanElement>(null);
  useEffect(() => {
    if (ref.current) {
      katex.render(children, ref.current, { throwOnError: false, displayMode: display });
    }
  }, [children, display]);
  return <span ref={ref} />;
}

function MathBlock({ children }: { children: string }) {
  return <div className="my-4 p-3 bg-zinc-100 dark:bg-zinc-800 rounded-lg overflow-x-auto text-center"><Tex display>{children}</Tex></div>;
}

export default function HowItWorksClient({ lang }: { lang: string }) {
  const t = getDictionary(lang);

  const sections = [
    {
      title: "1. The Problem: Kitten Season Resource Allocation",
      content: (
        <div className="space-y-3">
          <p>Every spring, cat shelters face a surge in intake — kitten season. With fixed budgets and limited space, managers must decide: <em>how do we allocate our intervention budget to minimize overflow?</em></p>
          <p>ShelterPulse models this as a <strong>constrained stochastic optimization problem</strong>:</p>
          <MathBlock>{String.raw`\min_{\mathbf{x}} \; \mathbb{E}\left[\text{Overflow}(\mathbf{x})\right] \quad \text{s.t.} \quad \sum_{i=1}^{4} x_i \leq B`}</MathBlock>
          <p>Where <Tex>{String.raw`\mathbf{x} = (x_1, x_2, x_3, x_4)`}</Tex> is the budget allocation across 4 strategies, and <Tex>{String.raw`B`}</Tex> is the total intervention budget (hard limit, e.g. $5,000).</p>
          <p>The 4 intervention strategies are:</p>
          <ul className="list-disc pl-5 space-y-1">
            <li><strong>Foster Support</strong> — subsidize foster families to increase network capacity</li>
            <li><strong>Extra Clinic Hours</strong> — more vet-tech time to speed medical clearance</li>
            <li><strong>Temporary Isolation</strong> — expand quarantine slots during peak URI season</li>
            <li><strong>Adoption Events</strong> — reduce adoption wait time with marketing/events</li>
          </ul>
        </div>
      )
    },
    {
      title: "2. Discrete-Event Simulation (SimPy Engine)",
      content: (
        <div className="space-y-3">
          <p>The core engine is a <strong>discrete-event simulation</strong> built with SimPy. Each cat is an independent process flowing through the shelter:</p>
          <MathBlock>{String.raw`\text{Intake} \rightarrow \text{Assessment} \rightarrow \text{Isolation} \rightarrow \text{Medical} \rightarrow \text{Housing} \rightarrow \text{Foster} \rightarrow \text{Adoption}`}</MathBlock>
          <p><strong>Intake model:</strong> Non-homogeneous Poisson process with seasonal multiplier:</p>
          <MathBlock>{String.raw`\lambda(t) = \lambda_0 \cdot m(t), \quad m(t) = \begin{cases} \text{surge\_multiplier} & \text{during kitten season} \\ 1.0 & \text{otherwise} \end{cases}`}</MathBlock>
          <p>For example, <Tex>{String.raw`\lambda_0 = 3.5`}</Tex> cats/day with <Tex>{String.raw`m = 2.5`}</Tex> surge means <Tex>{String.raw`\lambda = 8.75`}</Tex> cats/day at peak.</p>
          <p><strong>Service times</strong> are drawn from parametric distributions:</p>
          <ul className="list-disc pl-5 space-y-1">
            <li>Assessment: <Tex>{String.raw`\text{Exp}(\mu = 0.25\text{h})`}</Tex> for adults, <Tex>{String.raw`0.5\text{h}`}</Tex> for neonatals</li>
            <li>Isolation: <Tex>{String.raw`\text{Gamma}(k=2, \theta=7) \approx 14 \text{ days}`}</Tex></li>
            <li>Medical clearance: <Tex>{String.raw`\text{Gamma}(k=3, \theta=8) \approx 24\text{h}`}</Tex> for sick cats</li>
            <li>Adoption wait: <Tex>{String.raw`\text{Gamma}(k=2, \theta=5)`}</Tex> for kittens, <Tex>{String.raw`\text{Exp}(12\text{ days})`}</Tex> for adults</li>
          </ul>
          <p><strong>Overflow</strong> is measured in <em>cat-days</em>: each hour a cat spends in housing beyond capacity contributes to the overflow metric.</p>
        </div>
      )
    },
    {
      title: "3. The Scenario Schema & Seasonal Events",
      content: (
        <div className="space-y-3">
          <p>A scenario defines one or more <strong>seasonal events</strong> that modify intake rates during specific time windows:</p>
          <div className="my-3 bg-zinc-800 dark:bg-zinc-950 text-zinc-100 rounded-lg p-4 font-mono text-xs overflow-x-auto">
            <pre>{`seasonal_events:
  - name: "Kitten Season Surge"
    start_day: 1
    duration_days: 45
    intake_multiplier: 2.5

# Full scenario also defines:
housing_capacity: 35
isolation_capacity: 5
intake_rate_per_day: 3.8
workforce: [{ role: vet_tech, fte: 1.5 }]
foster_network: { capacity: 8 }
total_intervention_budget: 5000`}</pre>
          </div>
          <p>The <strong>what-if scenario</strong> system lets you change any parameter and re-run: <em>&ldquo;What if intake increases 20%? What if we add 5 isolation slots?&rdquo;</em></p>
          <p>Multiple seasonal events can stack — e.g., kitten season (day 1–45) + holiday surrender spike (day 60–70, 1.5× multiplier).</p>
        </div>
      )
    },
    {
      title: "4. Budget Allocation & Intervention Effects",
      content: (
        <div className="space-y-3">
          <p>Each fraction of budget allocated to a strategy produces a <strong>concrete resource change</strong>:</p>
          <MathBlock>{String.raw`\text{extra\_foster\_slots} = \left\lfloor \frac{x_1 \cdot B}{200} \right\rfloor, \quad \text{extra\_vet\_FTE} = \frac{x_2 \cdot B}{5000}`}</MathBlock>
          <table className="w-full text-xs border border-zinc-200 dark:border-zinc-700 rounded mt-2">
            <thead>
              <tr className="bg-zinc-100 dark:bg-zinc-800">
                <th className="p-2 text-left">Strategy</th>
                <th className="p-2 text-left">Formula</th>
                <th className="p-2 text-left">Real-world mechanism</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-t border-zinc-200 dark:border-zinc-700"><td className="p-2">Foster</td><td className="p-2"><Tex>{String.raw`\lfloor x_1 B / 200 \rfloor`}</Tex> slots</td><td className="p-2">Subsidize supplies for foster homes</td></tr>
              <tr className="border-t border-zinc-200 dark:border-zinc-700"><td className="p-2">Clinic</td><td className="p-2"><Tex>{String.raw`x_2 B / 5000`}</Tex> FTE</td><td className="p-2">Overtime / contract vet hours</td></tr>
              <tr className="border-t border-zinc-200 dark:border-zinc-700"><td className="p-2">Isolation</td><td className="p-2"><Tex>{String.raw`\lfloor x_3 B / 400 \rfloor`}</Tex> slots</td><td className="p-2">Portable cages + bio supplies</td></tr>
              <tr className="border-t border-zinc-200 dark:border-zinc-700"><td className="p-2">Adoption</td><td className="p-2"><Tex>{String.raw`\max(0.5, 1 - x_4 B / 5000)`}</Tex> wait mult.</td><td className="p-2">Events, fee waivers, marketing</td></tr>
            </tbody>
          </table>
          <p className="mt-3">The constraint: <Tex>{String.raw`x_1 + x_2 + x_3 + x_4 \leq 1.0`}</Tex>. A split of <Tex>{String.raw`(40\%, 10\%, 10\%, 40\%)`}</Tex> means $2,000 to foster, $500 each to clinic & isolation, $2,000 to adoption events.</p>
        </div>
      )
    },
    {
      title: "5. Monte Carlo & Common Random Numbers",
      content: (
        <div className="space-y-3">
          <p>The simulation is stochastic — each run produces different results. We use <strong>Monte Carlo replication</strong> with <strong>Common Random Numbers (CRN)</strong> for fair comparison:</p>
          <MathBlock>{String.raw`\bar{Y}(\mathbf{x}) = \frac{1}{N} \sum_{i=1}^{N} Y(\mathbf{x}, \omega_i), \quad \omega_i \text{ shared across all candidates}`}</MathBlock>
          <p>By using the <strong>same random seeds</strong> for each candidate allocation, differences in overflow are due to the allocation — not random noise.</p>
          <p><strong>Confidence intervals</strong> (95%):</p>
          <MathBlock>{String.raw`\text{CI}_{95} = \bar{Y} \pm 1.96 \cdot \frac{\sigma}{\sqrt{N}}`}</MathBlock>
          <p>With <Tex>{String.raw`N=32`}</Tex> replications, a result of <Tex>{String.raw`234 \pm 18`}</Tex> overflow cat-days means we{"'"}re 95% confident the true expected value is in <Tex>{String.raw`[216, 252]`}</Tex>.</p>
        </div>
      )
    },
    {
      title: "6. Bayesian Optimization (GP + Expected Improvement)",
      content: (
        <div className="space-y-3">
          <p>Evaluating every possible budget split is expensive (~2s per candidate). We use <strong>Bayesian Optimization</strong> to find the optimum efficiently:</p>
          <ol className="list-decimal pl-5 space-y-2">
            <li><strong>Surrogate model:</strong> Fit a Gaussian Process to observed (allocation → overflow) pairs</li>
            <li><strong>Acquisition function:</strong> Expected Improvement selects the next candidate to evaluate</li>
            <li><strong>Iterate:</strong> Evaluate, update GP, repeat until budget exhausted</li>
          </ol>
          <MathBlock>{String.raw`\text{EI}(\mathbf{x}) = \mathbb{E}\left[\max(f^* - f(\mathbf{x}), 0)\right]`}</MathBlock>
          <p>Where <Tex>{String.raw`f^*`}</Tex> is the best overflow seen so far. The GP models:</p>
          <MathBlock>{String.raw`f(\mathbf{x}) \sim \mathcal{GP}\left(\mu(\mathbf{x}),\; k(\mathbf{x}, \mathbf{x}')\right), \quad k = \text{RBF kernel}`}</MathBlock>
          <p>EI balances <strong>exploitation</strong> (try near known good points) vs <strong>exploration</strong> (try uncertain regions). We warm-start with named baselines then run 15–30 BO iterations.</p>
        </div>
      )
    },
    {
      title: "7. Sensitivity Analysis",
      content: (
        <div className="space-y-3">
          <p>Sensitivity analysis answers: <em>&ldquo;Which parameter matters most?&rdquo;</em></p>
          <p>We vary each input parameter <Tex>{String.raw`\pm 20\%`}</Tex> independently and measure the change in overflow:</p>
          <MathBlock>{String.raw`\Delta\text{Overflow}(p) = \text{Overflow}(p + 20\%) - \text{Overflow}(p - 20\%)`}</MathBlock>
          <p>Parameters with large <Tex>{String.raw`\Delta\text{Overflow}`}</Tex> are the ones worth investing in. The tornado chart ranks them — typically <strong>intake rate</strong> and <strong>housing capacity</strong> dominate.</p>
        </div>
      )
    },
    {
      title: "8. Try It Yourself",
      content: (
        <div className="space-y-3">
          <p>Two ways to explore:</p>
          <div className="flex gap-3 mt-2">
            <Link href={`/${lang}/demo`} className="px-4 py-2 bg-amber-500 hover:bg-amber-400 text-white font-semibold rounded-lg text-sm transition-colors">Guided Demo →</Link>
            <Link href={`/${lang}/simulate`} className="px-4 py-2 border border-zinc-300 dark:border-zinc-600 text-zinc-700 dark:text-zinc-300 font-semibold rounded-lg text-sm hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors">Custom Builder →</Link>
          </div>
        </div>
      )
    },
  ];

  const [expanded, setExpanded] = useState<boolean[]>(sections.map(() => false));
  const toggle = (i: number) => setExpanded(prev => prev.map((v, j) => j === i ? !v : v));

  return (
    <main className="min-h-screen bg-zinc-50 dark:bg-zinc-950 py-12 px-4">
      <div className="max-w-3xl mx-auto">
        <h1 className="text-3xl font-bold text-zinc-900 dark:text-zinc-50 mb-2">{t.howItWorks.title}</h1>
        <p className="text-zinc-500 dark:text-zinc-400 mb-8">{t.howItWorks.subtitle}</p>
        <div className="space-y-3">
          {sections.map((s, i) => (
            <div key={i} className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-lg overflow-hidden">
              <button onClick={() => toggle(i)} className="w-full flex items-center justify-between px-5 py-4 text-left hover:bg-zinc-50 dark:hover:bg-zinc-800">
                <span className="font-semibold text-zinc-900 dark:text-zinc-50">{s.title}</span>
                <span className="text-amber-500 text-xl font-mono">{expanded[i] ? '−' : '+'}</span>
              </button>
              {expanded[i] && <div className="px-5 pb-5 text-zinc-700 dark:text-zinc-300 text-sm leading-relaxed">{s.content}</div>}
            </div>
          ))}
        </div>
      </div>
    </main>
  );
}
