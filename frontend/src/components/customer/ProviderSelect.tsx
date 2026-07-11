import type { Provider } from "../../types/api";

interface ProviderSelectProps {
  providers: Provider[];
  value: string;
  onChange: (id: string) => void;
}

/** LLM provider picker in the top bar; unavailable providers are disabled. */
export function ProviderSelect({ providers, value, onChange }: ProviderSelectProps) {
  return (
    <label
      title="Choose which model answers - options with a key configured are enabled"
      className="inline-flex cursor-pointer items-center gap-1.5 rounded-full border border-line bg-white/[0.03] px-[13px] py-[7px] text-[13px] font-medium text-muted transition duration-200 hover:border-line-strong hover:text-ink"
    >
      🧠{" "}
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="max-w-[220px] cursor-pointer border-none bg-transparent text-[13px] font-semibold text-ink outline-none"
      >
        {providers.map((provider) => (
          <option
            key={provider.id}
            value={provider.id}
            disabled={!provider.available}
            className="bg-panel-solid text-ink disabled:text-faint"
          >
            {provider.available ? provider.label : `${provider.label} - no key`}
          </option>
        ))}
      </select>
    </label>
  );
}
