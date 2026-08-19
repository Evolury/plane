import type { TDropdownProps } from "../types";

export type MemberDropdownProps = TDropdownProps & {
  button?: React.ReactNode;
  dropdownArrow?: boolean;
  dropdownArrowClassName?: string;
  placeholder?: string;
  tooltipContent?: string;
  onClose?: () => void;
  showUserDetails?: boolean;
  // Evolury: o `AssigneeDropdown` usa isto para pôr o seletor de etapa de
  // "Minhas tarefas" ao lado do nome quando o responsável sou eu (ADR 0016).
  // O dropdown genérico não conhece o conceito.
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
