/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { SetStateAction } from "react";
import { observer } from "mobx-react";
import { GripVertical } from "lucide-react";
import { EIconSize, STATE_TRACKER_ELEMENTS } from "@plane/constants";
// plane imports
import { EditIcon, StateGroupIcon } from "@plane/propel/icons";
import type { IState, TStateOperationsCallbacks } from "@plane/types";
// local imports
import { useProjectState } from "@/hooks/store/use-project-state";
import { StageBuckets, StateDelete, StateMarksAsCompletion, StateMarksAsDefault } from "./options";

type TBaseStateItemTitleProps = {
  stateCount: number;
  state: IState;
  shouldShowDescription?: boolean;
  setUpdateStateModal: (value: SetStateAction<boolean>) => void;
};

type TEnabledStateItemTitleProps = TBaseStateItemTitleProps & {
  disabled: false;
  stateOperationsCallbacks: Pick<
    TStateOperationsCallbacks,
    | "markStateAsDefault"
    | "deleteState"
    | "markStateAsCompletion"
    | "getCompletionStateInfo"
    // Evolury: baldes de vencimento (ADR 0014). Opcionais no tipo de origem —
    // estado de projeto não os passa e não vê nada na tela.
    | "markStageBucket"
    | "getStageBucketInfo"
    | "toggleStageAutomation"
  >;
  shouldTrackEvents: boolean;
};

type TDisabledStateItemTitleProps = TBaseStateItemTitleProps & {
  disabled: true;
};

export type TStateItemTitleProps = TEnabledStateItemTitleProps | TDisabledStateItemTitleProps;

export const StateItemTitle = observer(function StateItemTitle(props: TStateItemTitleProps) {
  const { stateCount, setUpdateStateModal, disabled, state, shouldShowDescription = true } = props;
  // store hooks
  const { getStatePercentageInGroup } = useProjectState();
  // derived values
  const statePercentage = getStatePercentageInGroup(state.id);
  const percentage = statePercentage ? statePercentage / 100 : undefined;

  return (
    <div className="flex w-full items-center justify-between gap-2">
      <div className="flex items-center gap-1 px-1">
        {/* draggable indicator */}
        {!disabled && stateCount != 1 && (
          <div className="absolute -left-1.5 hidden h-3 w-3 flex-shrink-0 cursor-pointer items-center justify-center rounded-xs bg-surface-2 text-secondary transition-colors group-hover:flex hover:text-primary">
            <GripVertical className="h-3 w-3" />
          </div>
        )}
        {/* state icon */}
        <div className="flex-shrink-0">
          <StateGroupIcon stateGroup={state.group} color={state.color} size={EIconSize.XL} percentage={percentage} />
        </div>
        {/* state title and description */}
        <div className="min-h-5 px-2 text-13">
          <h6 className="text-13 font-medium">{state.name}</h6>
          {shouldShowDescription && <p className="text-11 text-secondary">{state.description}</p>}
        </div>
      </div>
      {/* Evolury: baldes de vencimento e trava da varredura (ADR 0014).
          FORA do bloco de hover de propósito: marcação não é ação, é
          INFORMAÇÃO — saber qual etapa recebe as vencidas não pode exigir
          passar o mouse por oito linhas. Quem some no hover é só o que está
          desmarcado; ver `StageBuckets`. */}
      {!disabled &&
        props.stateOperationsCallbacks.markStageBucket &&
        props.stateOperationsCallbacks.getStageBucketInfo &&
        props.stateOperationsCallbacks.toggleStageAutomation && (
          <StageBuckets
            stageId={state.id}
            marcacoes={props.stateOperationsCallbacks.getStageBucketInfo(state.id)}
            onMarcar={(balde, ativo) => props.stateOperationsCallbacks.markStageBucket!(state.id, balde, ativo)}
            onAlternarAutomacao={(desativada) =>
              props.stateOperationsCallbacks.toggleStageAutomation!(state.id, desativada)
            }
          />
        )}
      {!disabled && (
        <div className="hidden items-center gap-2 group-hover:flex">
          {/* Evolury: destino do botão de concluir, só no grupo concluído e só
              onde a tela sabe responder quem é o destino (ADR 0009) */}
          {state.group === "completed" &&
            props.stateOperationsCallbacks.markStateAsCompletion &&
            props.stateOperationsCallbacks.getCompletionStateInfo && (
              <div className="flex-shrink-0 text-11 transition-all">
                <StateMarksAsCompletion
                  {...props.stateOperationsCallbacks.getCompletionStateInfo(state.id)}
                  onMark={() => props.stateOperationsCallbacks.markStateAsCompletion!(state.id)}
                />
              </div>
            )}
          {/* state mark as default option */}
          <div className="flex-shrink-0 text-11 transition-all">
            <StateMarksAsDefault
              stateId={state.id}
              isDefault={state.default ? true : false}
              markStateAsDefaultCallback={props.stateOperationsCallbacks.markStateAsDefault}
            />
          </div>
          {/* state edit options */}
          <div className="flex items-center gap-1 transition-all">
            <button
              className="flex h-5 w-5 flex-shrink-0 cursor-pointer items-center justify-center overflow-hidden rounded-sm text-secondary transition-colors hover:bg-layer-1 hover:text-primary"
              onClick={() => setUpdateStateModal(true)}
              data-ph-element={STATE_TRACKER_ELEMENTS.STATE_LIST_EDIT_BUTTON}
            >
              <EditIcon className="h-3 w-3" />
            </button>
            <StateDelete
              totalStates={stateCount}
              state={state}
              deleteStateCallback={props.stateOperationsCallbacks.deleteState}
              shouldTrackEvents={props.shouldTrackEvents}
            />
          </div>
        </div>
      )}
    </div>
  );
});
