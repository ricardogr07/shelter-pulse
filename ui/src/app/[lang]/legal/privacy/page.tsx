export default function PrivacyPage() {
  return (
    <main className="min-h-screen bg-zinc-50 dark:bg-zinc-950 py-12 px-4">
      <div className="max-w-2xl mx-auto prose prose-zinc dark:prose-invert">
        <h1 className="text-3xl font-bold text-zinc-900 dark:text-zinc-50 mb-6">Privacy Policy</h1>
        <p className="text-sm text-zinc-500 dark:text-zinc-400 mb-8">Last updated: July 2026</p>

        <section className="mb-8">
          <h2 className="text-xl font-semibold text-zinc-800 dark:text-zinc-200 mb-3">Data Controller</h2>
          <p className="text-zinc-600 dark:text-zinc-400">
            ShelterPulse is an open-source project maintained by Ricardo Garc{"í"}a Ram{"í"}rez.
            For data-related inquiries, contact us via the project&apos;s GitHub repository:
            {" "}<a href="https://github.com/ricardogr07/shelter-pulse" className="text-amber-600 underline">github.com/ricardogr07/shelter-pulse</a>.
          </p>
        </section>

        <section className="mb-8">
          <h2 className="text-xl font-semibold text-zinc-800 dark:text-zinc-200 mb-3">What Data We Collect</h2>
          <p className="text-zinc-600 dark:text-zinc-400 mb-3">
            When you explicitly consent via the checkbox on the simulation page, we store:
          </p>
          <ul className="list-disc pl-6 text-zinc-600 dark:text-zinc-400 space-y-1">
            <li>Shelter parameters you entered (capacity, budget, intake rates, etc.)</li>
            <li>Optimization results (allocation percentages, overflow metrics)</li>
            <li>A timestamp of when the optimization was run</li>
            <li>A one-way hash (SHA-256, truncated) of your IP address for audit purposes</li>
            <li>Whether you marked the data as test/demo data</li>
          </ul>
          <p className="text-zinc-600 dark:text-zinc-400 mt-3">
            We do <strong>not</strong> collect or store:
          </p>
          <ul className="list-disc pl-6 text-zinc-600 dark:text-zinc-400 space-y-1">
            <li>Raw IP addresses (only a truncated, irreversible hash)</li>
            <li>Cookies or tracking identifiers</li>
            <li>Personal information beyond what you enter in the form</li>
            <li>Browser fingerprints or analytics data</li>
          </ul>
        </section>

        <section className="mb-8">
          <h2 className="text-xl font-semibold text-zinc-800 dark:text-zinc-200 mb-3">Legal Basis</h2>
          <p className="text-zinc-600 dark:text-zinc-400">
            Data storage is based on your <strong>explicit consent</strong> provided via the
            &quot;I consent to storing my optimization inputs&quot; checkbox. If you do not check
            this box, your optimization runs normally but no data is persisted. The consent
            decision itself is logged for audit purposes (even when declined).
          </p>
        </section>

        <section className="mb-8">
          <h2 className="text-xl font-semibold text-zinc-800 dark:text-zinc-200 mb-3">Purpose of Data Storage</h2>
          <ul className="list-disc pl-6 text-zinc-600 dark:text-zinc-400 space-y-1">
            <li>Enabling run history so you can reference previous optimization results</li>
            <li>Matching your shelter to show past runs when you return</li>
            <li>Aggregate analytics to improve the optimization algorithms</li>
          </ul>
        </section>

        <section className="mb-8">
          <h2 className="text-xl font-semibold text-zinc-800 dark:text-zinc-200 mb-3">Data Retention</h2>
          <p className="text-zinc-600 dark:text-zinc-400">
            Stored optimization runs are retained indefinitely for analytics and run history
            purposes. You may request deletion at any time (see below).
          </p>
        </section>

        <section className="mb-8">
          <h2 className="text-xl font-semibold text-zinc-800 dark:text-zinc-200 mb-3">Data Storage and Security</h2>
          <p className="text-zinc-600 dark:text-zinc-400">
            Data is stored in a DuckDB database on AWS Elastic File System (EFS) in the
            us-east-1 region. Access is restricted to the application&apos;s compute layer
            (ECS tasks and Lambda functions). No third parties have access to the raw data.
          </p>
        </section>

        <section className="mb-8">
          <h2 className="text-xl font-semibold text-zinc-800 dark:text-zinc-200 mb-3">Cookies</h2>
          <p className="text-zinc-600 dark:text-zinc-400">
            ShelterPulse does not set any cookies. All consent state is managed in-memory
            within the browser session and is not persisted client-side.
          </p>
        </section>

        <section className="mb-8">
          <h2 className="text-xl font-semibold text-zinc-800 dark:text-zinc-200 mb-3">Your Rights</h2>
          <p className="text-zinc-600 dark:text-zinc-400 mb-3">You have the right to:</p>
          <ul className="list-disc pl-6 text-zinc-600 dark:text-zinc-400 space-y-1">
            <li><strong>Access</strong> your stored data by using the shelter matching feature</li>
            <li><strong>Delete</strong> your data by submitting a request via GitHub Issues</li>
            <li><strong>Withdraw consent</strong> at any time by unchecking the consent box (applies to future runs only)</li>
          </ul>
        </section>

        <section className="mb-8">
          <h2 className="text-xl font-semibold text-zinc-800 dark:text-zinc-200 mb-3">Contact</h2>
          <p className="text-zinc-600 dark:text-zinc-400">
            For data deletion requests or privacy inquiries, open an issue at:{" "}
            <a href="https://github.com/ricardogr07/shelter-pulse/issues" className="text-amber-600 underline">
              github.com/ricardogr07/shelter-pulse/issues
            </a>
          </p>
        </section>

        <section className="mb-8">
          <h2 className="text-xl font-semibold text-zinc-800 dark:text-zinc-200 mb-3">Changes to This Policy</h2>
          <p className="text-zinc-600 dark:text-zinc-400">
            We may update this policy as the project evolves. Changes will be reflected in
            the &quot;Last updated&quot; date above and committed to the public repository.
          </p>
        </section>
      </div>
    </main>
  );
}
