/**
 * ProfilePanel - displays DBT profile information, connection status, schema, and macros
 */

import { useEffect, useState } from 'react';
import { useSessionStore } from '../store/sessionStore';
import { CollapsibleSection, DetailSection } from './chat/CollapsibleSection';
import { Database, CheckCircle, XCircle, AlertCircle, RefreshCw, Table, Code, Edit } from 'lucide-react';
import { FileEditor } from './editor/FileEditor';
import { FullscreenEditorModal } from './editor/FullscreenEditorModal';
import { api } from '../lib/api';

export function ProfilePanel() {
  const { profileInfo, isProfileLoading, profileError, loadProfileInfo } = useSessionStore();

  // Editing states
  const [editingSchema, setEditingSchema] = useState(false);
  const [fullscreenSchema, setFullscreenSchema] = useState(false);
  const [editingMacro, setEditingMacro] = useState<string | null>(null);
  const [fullscreenMacro, setFullscreenMacro] = useState<string | null>(null);

  // Load profile info when component mounts
  useEffect(() => {
    if (!profileInfo && !isProfileLoading) {
      loadProfileInfo();
    }
  }, []);

  const handleRefresh = () => {
    loadProfileInfo();
  };

  // Save handlers
  const handleSaveSchema = async (content: string) => {
    await api.files.updateSchema(content);
    setEditingSchema(false);
    setFullscreenSchema(false);
    // Refresh profile info to show updated content
    await loadProfileInfo();
  };

  const handleSaveMacro = async (filename: string, content: string) => {
    // Check if this is an existing macro or new one
    const existingMacro = profileInfo?.macros.files.find(f => f.filename === filename);
    if (existingMacro) {
      await api.files.updateMacro(filename, content);
    } else {
      await api.files.createMacro(filename, content);
    }
    setEditingMacro(null);
    setFullscreenMacro(null);
    // Refresh profile info to show updated content
    await loadProfileInfo();
  };

  // Loading state
  if (isProfileLoading && !profileInfo) {
    return (
      <div className="flex flex-col h-full p-4">
        <div className="flex items-center gap-2 mb-4">
          <Database size={20} className="text-muted-foreground" />
          <div className="h-5 w-32 bg-muted animate-pulse rounded" />
        </div>
        <div className="space-y-3">
          <div className="h-20 bg-muted animate-pulse rounded" />
          <div className="h-20 bg-muted animate-pulse rounded" />
          <div className="h-20 bg-muted animate-pulse rounded" />
        </div>
      </div>
    );
  }

  // Error state
  if (profileError) {
    return (
      <div className="flex flex-col h-full p-4">
        <div className="flex items-center gap-2 mb-4 text-destructive">
          <AlertCircle size={20} />
          <h3 className="font-semibold">Error Loading Profile</h3>
        </div>
        <p className="text-sm text-muted-foreground mb-4">{profileError}</p>
        <button
          onClick={handleRefresh}
          className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
        >
          Retry
        </button>
      </div>
    );
  }

  // No profile info state
  if (!profileInfo) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-4 text-center">
        <Database size={48} className="text-muted-foreground mb-4" />
        <h3 className="font-semibold mb-2">No Profile Information</h3>
        <p className="text-sm text-muted-foreground mb-4">
          Load a session to view profile details
        </p>
      </div>
    );
  }

  // Format timestamp
  const formatTimestamp = (isoString: string) => {
    const date = new Date(isoString);
    return date.toLocaleTimeString();
  };

  // Determine connection status icon and color
  const getStatusIcon = () => {
    switch (profileInfo.connection.status) {
      case 'connected':
        return <CheckCircle size={16} className="text-green-500" />;
      case 'disconnected':
        return <XCircle size={16} className="text-red-500" />;
      default:
        return <AlertCircle size={16} className="text-yellow-500" />;
    }
  };

  return (
    <div className="flex flex-col h-full overflow-y-auto">
      {/* Header */}
      <div className="px-4 py-3 border-b border-border flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Database size={20} className="text-muted-foreground" />
          <h3 className="font-semibold">Profile Information</h3>
        </div>
        <button
          onClick={handleRefresh}
          disabled={isProfileLoading}
          className="p-1 hover:bg-accent rounded transition-colors disabled:opacity-50"
          title="Refresh profile information"
        >
          <RefreshCw size={16} className={isProfileLoading ? 'animate-spin' : ''} />
        </button>
      </div>

      {/* Content */}
      <div className="p-4 space-y-4">
        {/* Connection Status */}
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-sm font-semibold">
            {getStatusIcon()}
            <span>Connection Status</span>
          </div>
          <div className="pl-6 space-y-1">
            <div className="text-xs text-muted-foreground">
              Status: <span className="font-medium text-foreground capitalize">
                {profileInfo.connection.status}
              </span>
            </div>
            <div className="text-xs text-muted-foreground">
              Last checked: {formatTimestamp(profileInfo.connection.last_checked)}
            </div>
            {profileInfo.connection.error && (
              <div className="text-xs text-destructive mt-2 p-2 bg-destructive/10 rounded">
                {profileInfo.connection.error}
              </div>
            )}
          </div>
        </div>

        {/* Profile Configuration */}
        <div className="space-y-2">
          <div className="text-sm font-semibold">Configuration</div>
          <div className="space-y-2">
            <DetailSection label="Profile Name">
              {profileInfo.profile_name}
            </DetailSection>
            <DetailSection label="Profiles Directory" monospace>
              {profileInfo.config.profiles_dir}
            </DetailSection>
            <DetailSection label="DBT Mode">
              {profileInfo.config.is_using_local_dbt ? 'Local' : 'Embedded'}
            </DetailSection>
          </div>
        </div>

        {/* Schema Information */}
        <CollapsibleSection
          title="Schema"
          icon={<Table size={16} />}
          defaultExpanded={false}
        >
          {profileInfo.schema.location || editingSchema ? (
            <div className="space-y-2">
              <div className="text-xs text-muted-foreground mb-2">
                Defines your database tables and columns.{' '}
                <a
                  href="https://docs.getdbt.com/reference/source-properties"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-primary hover:underline"
                >
                  Learn more ↗
                </a>
              </div>
              {profileInfo.schema.location && (
                <>
                  <DetailSection label="Sources">
                    {profileInfo.schema.sources_count} {profileInfo.schema.sources_count === 1 ? 'source' : 'sources'}
                  </DetailSection>
                  <DetailSection label="Tables">
                    {profileInfo.schema.tables_count} {profileInfo.schema.tables_count === 1 ? 'table' : 'tables'}
                  </DetailSection>
                </>
              )}

              {/* View mode or Edit mode */}
              {editingSchema ? (
                <div className="mt-3 border border-border rounded overflow-hidden" style={{ height: '400px' }}>
                  <FileEditor
                    filename="schema.yml"
                    content={profileInfo.schema.content || ''}
                    language="yaml"
                    onSave={handleSaveSchema}
                    onCancel={() => setEditingSchema(false)}
                    onFullscreen={() => {
                      setEditingSchema(false);
                      setFullscreenSchema(true);
                    }}
                  />
                </div>
              ) : profileInfo.schema.content ? (
                <>
                  <div className="mt-3">
                    <pre className="text-xs font-mono bg-muted p-3 rounded overflow-x-auto max-h-96 overflow-y-auto whitespace-pre">
                      {profileInfo.schema.content}
                    </pre>
                  </div>
                  <button
                    onClick={() => setEditingSchema(true)}
                    className="flex items-center gap-1 text-sm text-primary hover:underline mt-2"
                  >
                    <Edit size={14} />
                    Edit Schema
                  </button>
                </>
              ) : (
                <button
                  onClick={() => setEditingSchema(true)}
                  className="flex items-center gap-1 text-sm text-primary hover:underline mt-2"
                >
                  <Edit size={14} />
                  Create Schema
                </button>
              )}
            </div>
          ) : (
            <div>
              <p className="text-sm text-muted-foreground mb-2">No schema file found</p>
              <button
                onClick={() => setEditingSchema(true)}
                className="flex items-center gap-1 text-sm text-primary hover:underline"
              >
                <Edit size={14} />
                Create Schema
              </button>
            </div>
          )}
        </CollapsibleSection>

        {/* Fullscreen Schema Editor Modal */}
        {fullscreenSchema && (
          <FullscreenEditorModal
            isOpen={fullscreenSchema}
            filename="schema.yml"
            content={profileInfo?.schema.content || ''}
            language="yaml"
            onSave={handleSaveSchema}
            onClose={() => setFullscreenSchema(false)}
          />
        )}

        {/* Macros */}
        <CollapsibleSection
          title="Macros"
          icon={<Code size={16} />}
          defaultExpanded={false}
        >
          <div className="space-y-2">
            <div className="text-xs text-muted-foreground mb-2">
              Reusable SQL code snippets (like functions).{' '}
              <a
                href="https://docs.getdbt.com/docs/build/jinja-macros"
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary hover:underline"
              >
                Learn more ↗
              </a>
            </div>
            {profileInfo.macros.location && (
              <DetailSection label="Available">
                {profileInfo.macros.count} {profileInfo.macros.count === 1 ? 'macro' : 'macros'}
              </DetailSection>
            )}
            {profileInfo.macros.files.length > 0 && (
              <div className="mt-3 space-y-3">
                {profileInfo.macros.files.map((file) => (
                  <div key={file.filename} className="border border-border rounded p-2">
                    <div className="flex items-center justify-between mb-1">
                      <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                        {file.filename}
                      </div>
                    </div>
                    {/* View mode or Edit mode */}
                    {editingMacro === file.filename ? (
                      <div className="border border-border rounded overflow-hidden" style={{ height: '300px' }}>
                        <FileEditor
                          filename={file.filename}
                          content={file.content}
                          language="sql"
                          onSave={(content) => handleSaveMacro(file.filename, content)}
                          onCancel={() => setEditingMacro(null)}
                          onFullscreen={() => {
                            setEditingMacro(null);
                            setFullscreenMacro(file.filename);
                          }}
                        />
                      </div>
                    ) : (
                      <>
                        <pre className="text-xs font-mono bg-muted p-3 rounded overflow-x-auto max-h-96 overflow-y-auto whitespace-pre">
                          {file.content}
                        </pre>
                        <button
                          onClick={() => setEditingMacro(file.filename)}
                          className="flex items-center gap-1 text-sm text-primary hover:underline mt-2"
                        >
                          <Edit size={14} />
                          Edit
                        </button>
                      </>
                    )}
                  </div>
                ))}
              </div>
            )}
            {!profileInfo.macros.location || profileInfo.macros.files.length === 0 ? (
              <p className="text-sm text-muted-foreground">No macros found</p>
            ) : null}
          </div>
        </CollapsibleSection>

        {/* Fullscreen Macro Editor Modals */}
        {fullscreenMacro && (
          <FullscreenEditorModal
            isOpen={!!fullscreenMacro}
            filename={fullscreenMacro}
            content={profileInfo?.macros.files.find(f => f.filename === fullscreenMacro)?.content || ''}
            language="sql"
            onSave={(content) => handleSaveMacro(fullscreenMacro, content)}
            onClose={() => setFullscreenMacro(null)}
          />
        )}
      </div>
    </div>
  );
}
