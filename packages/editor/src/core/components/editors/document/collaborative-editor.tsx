/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import React, { useMemo } from "react";
// plane imports
import { cn } from "@plane/utils";
// components
import { PageRenderer } from "@/components/editors";
// constants
import { DEFAULT_DISPLAY_CONFIG } from "@/constants/config";
// contexts
import { CollaborationProvider, useCollaboration } from "@/contexts/collaboration-context";
import { EditorTranslationProvider } from "@/providers/translation";
// helpers
import { getEditorClassNames } from "@/helpers/common";
// hooks
import { useCollaborativeEditor } from "@/hooks/use-collaborative-editor";
// types
import type { EditorRefApi, ICollaborativeDocumentEditorProps } from "@/types";

// Inner component that has access to collaboration context
function CollaborativeDocumentEditorInner(props: ICollaborativeDocumentEditorProps) {
  const {
    aiHandler,
    bubbleMenuEnabled = true,
    containerClassName,
    documentLoaderClassName,
    extensions = [],
    disabledExtensions,
    displayConfig = DEFAULT_DISPLAY_CONFIG,
    editable,
    editorClassName = "",
    editorProps,
    extendedEditorProps,
    fileHandler,
    flaggedExtensions,
    forwardedRef,
    getEditorMetaData,
    handleEditorReady,
    id,
    dragDropEnabled = true,
    isTouchDevice,
    mentionHandler,
    onAssetChange,
    onChange,
    onEditorFocus,
    onTransaction,
    placeholder,
    tabIndex,
    user,
    extendedDocumentEditorProps,
    titleRef,
    updatePageProperties,
    isFetchingFallbackBinary,
  } = props;

  // Get non-null provider from context
  const { provider, state, actions } = useCollaboration();

  // Editor initialization with guaranteed non-null provider
  const { editor, titleEditor } = useCollaborativeEditor({
    provider,
    disabledExtensions,
    editable,
    editorClassName,
    editorProps,
    extendedEditorProps,
    extensions,
    fileHandler,
    flaggedExtensions,
    getEditorMetaData,
    forwardedRef,
    handleEditorReady,
    id,
    dragDropEnabled,
    isTouchDevice,
    mentionHandler,
    onAssetChange,
    onChange,
    onEditorFocus,
    onTransaction,
    placeholder,
    tabIndex,
    titleRef,
    updatePageProperties,
    user,
    actions,
  });

  const editorContainerClassNames = getEditorClassNames({
    noBorder: true,
    borderOnFocus: false,
    containerClassName,
  });

  // Show loader ONLY when cache is known empty and server hasn't synced yet
  const shouldShowSyncLoader = state.isCacheReady && !state.hasCachedContent && !state.isServerSynced;
  const shouldWaitForFallbackBinary = isFetchingFallbackBinary && !state.hasCachedContent && state.isServerDisconnected;
  const isLoading = shouldShowSyncLoader || shouldWaitForFallbackBinary;

  // Gate content rendering on isDocReady to prevent empty editor flash
  const showContentSkeleton = !state.isDocReady;

  if (!editor || !titleEditor) return null;

  return (
    <>
      <div
        className={cn(
          "transition-opacity duration-200",
          showContentSkeleton && !isLoading && "pointer-events-none opacity-0"
        )}
      >
        <PageRenderer
          aiHandler={aiHandler}
          bubbleMenuEnabled={bubbleMenuEnabled}
          displayConfig={displayConfig}
          documentLoaderClassName={documentLoaderClassName}
          disabledExtensions={disabledExtensions}
          extendedDocumentEditorProps={extendedDocumentEditorProps}
          editor={editor}
          flaggedExtensions={flaggedExtensions}
          titleEditor={titleEditor}
          editorContainerClassName={cn(editorContainerClassNames, "document-editor")}
          extendedEditorProps={extendedEditorProps}
          id={id}
          isLoading={isLoading}
          isTouchDevice={!!isTouchDevice}
          tabIndex={tabIndex}
          provider={provider}
          state={state}
        />
      </div>
    </>
  );
}

// Outer component that provides collaboration context
function CollaborativeDocumentEditor(props: ICollaborativeDocumentEditorProps) {
  const { id, realtimeConfig, serverHandler, user } = props;

  const token = useMemo(() => JSON.stringify(user), [user]);

  return (
    // O provedor precisa ficar ACIMA de quem constrói o editor: as extensões
    // chamam `useEditorTranslation()` durante a renderização, e contexto se lê
    // de cima. Sem isto o editor de documento cai no texto de reserva em inglês
    // — @plane/editor não depende de @plane/i18n de propósito, e quem sabe
    // traduzir é o app (ADR 0008). O rich-text e o lite-text já ganhavam o
    // provedor pelo EditorWrapper; os de documento não passavam por ele.
    <EditorTranslationProvider translate={props.translate}>
      <CollaborationProvider
        docId={id}
        serverUrl={realtimeConfig.url}
        authToken={token}
        onStateChange={serverHandler?.onStateChange}
      >
        <CollaborativeDocumentEditorInner {...props} />
      </CollaborationProvider>
    </EditorTranslationProvider>
  );
}

const CollaborativeDocumentEditorWithRef = React.forwardRef(function CollaborativeDocumentEditorWithRef(
  props: ICollaborativeDocumentEditorProps,
  ref: React.ForwardedRef<EditorRefApi>
) {
  return (
    <CollaborativeDocumentEditor key={props.id} {...props} forwardedRef={ref as React.MutableRefObject<EditorRefApi>} />
  );
});

CollaborativeDocumentEditorWithRef.displayName = "CollaborativeDocumentEditorWithRef";

export { CollaborativeDocumentEditorWithRef };
