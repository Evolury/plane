import type { TDropdownProps } from "../types";

export type MemberDropdownProps = TDropdownProps & {
  button?: React.ReactNode;
  dropdownArrow?: boolean;
  dropdownArrowClassName?: string;
  placeholder?: string;
  tooltipContent?: string;
  onClose?: () => void;
  showUserDetails?: boolean;
  // Evolury: quando o dropdown lista responsáveis de um work item, a linha do
  // usuário logado ganha o seletor de etapa de minhas tarefas (F7)
  workItemId?: string;
} & (
    | {
        multiple: false;
        onChange: (val: string | null) => void;
        value: string | null;
      }
    | {
        multiple: true;
        onChange: (val: string[]) => void;
        value: string[];
      }
  );
