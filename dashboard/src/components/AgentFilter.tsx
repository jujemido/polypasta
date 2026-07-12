import { Checkbox } from '@/components/ui/checkbox'
import { Label } from '@/components/ui/label'
import type { AgentMetric } from '../types'

interface Props {
  agents: AgentMetric[]
  selected: Set<string>
  onToggle: (id: string) => void
  onSelectAll: () => void
  onSelectNone: () => void
}

export function AgentFilter({ agents, selected, onToggle, onSelectAll, onSelectNone }: Props) {
  return (
    <fieldset className="space-y-2">
      <legend className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
        Filtrar agentes
      </legend>
      <div className="flex items-center gap-3 text-xs">
        <button onClick={onSelectAll} className="underline underline-offset-2 hover:no-underline">
          Todos
        </button>
        <span className="text-muted-foreground">·</span>
        <button onClick={onSelectNone} className="underline underline-offset-2 hover:no-underline">
          Ninguno
        </button>
      </div>
      <div className="flex flex-wrap gap-x-5 gap-y-1.5">
        {agents.map((agent) => (
          <div key={agent.agent_id} className="flex items-center gap-1.5">
            <Checkbox
              id={`f-${agent.agent_id}`}
              checked={selected.has(agent.agent_id)}
              onCheckedChange={() => onToggle(agent.agent_id)}
            />
            <Label
              htmlFor={`f-${agent.agent_id}`}
              className={`text-sm cursor-pointer ${selected.has(agent.agent_id) ? 'font-medium' : 'text-muted-foreground'}`}
            >
              {agent.name}
            </Label>
          </div>
        ))}
      </div>
    </fieldset>
  )
}