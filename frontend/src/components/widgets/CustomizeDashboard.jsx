import React from 'react'
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors
} from '@dnd-kit/core'
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
  useSortable
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import {
  XMarkIcon, Bars3Icon, EyeIcon, EyeSlashIcon,
  ChartBarIcon, FilmIcon, ClipboardDocumentListIcon,
  ExclamationTriangleIcon, MagnifyingGlassIcon,
  BellIcon, StarIcon
} from '@heroicons/react/24/outline'

const WIDGET_LABELS = {
  stats: 'Stats Overview',
  placements: 'Placement Pipeline',
  taskBreakdown: 'Tasks by Module',
  urgentActions: 'Urgent Action Items',
  needsAttention: 'Needs Attention',
  notifications: 'Recent Notifications',
  topCreators: 'Top Creators'
}

const WIDGET_ICONS = {
  stats: ChartBarIcon,
  placements: FilmIcon,
  taskBreakdown: ClipboardDocumentListIcon,
  urgentActions: ExclamationTriangleIcon,
  needsAttention: MagnifyingGlassIcon,
  notifications: BellIcon,
  topCreators: StarIcon
}

function SortableItem({ id, visible, onToggle }) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging
  } = useSortable({ id })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
    zIndex: isDragging ? 10 : 'auto'
  }

  const IconComponent = WIDGET_ICONS[id]

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`flex items-center gap-3 p-3 rounded-xl transition-colors ${
        visible ? 'bg-[#FAFBF9]' : 'bg-[#F5F7F4] opacity-60'
      }`}
    >
      <button
        {...attributes}
        {...listeners}
        className="flex-shrink-0 cursor-grab active:cursor-grabbing text-[#7A8580] hover:text-[#3D4A44] touch-none"
      >
        <Bars3Icon className="w-5 h-5" />
      </button>
      {IconComponent && <IconComponent className={`w-5 h-5 flex-shrink-0 ${visible ? 'text-[#5B8A72]' : 'text-[#7A8580]'}`} />}
      <span className={`flex-1 text-sm font-medium ${visible ? 'text-[#3D4A44]' : 'text-[#7A8580]'}`}>
        {WIDGET_LABELS[id]}
      </span>
      <button
        onClick={() => onToggle(id)}
        className={`flex-shrink-0 p-1.5 rounded-lg transition-colors ${
          visible
            ? 'text-[#5B8A72] hover:bg-[rgba(91,138,114,0.1)]'
            : 'text-[#7A8580] hover:bg-[#EEF1EC]'
        }`}
      >
        {visible ? <EyeIcon className="w-5 h-5" /> : <EyeSlashIcon className="w-5 h-5" />}
      </button>
    </div>
  )
}

export default function CustomizeDashboard({ isOpen, onClose, widgetOrder, widgetVisibility, onReorder, onToggleVisibility, onReset }) {
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  )

  const handleDragEnd = (event) => {
    const { active, over } = event
    if (!over || active.id === over.id) return
    const oldIndex = widgetOrder.indexOf(active.id)
    const newIndex = widgetOrder.indexOf(over.id)
    onReorder(arrayMove(widgetOrder, oldIndex, newIndex))
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-md bg-white shadow-2xl flex flex-col animate-slide-in-right">
        <div className="flex items-center justify-between p-6 border-b border-[#EEF1EC]">
          <div>
            <h2 className="text-xl font-semibold text-[#3D4A44]">Customize Dashboard</h2>
            <p className="text-sm text-[#7A8580] mt-1">Drag to reorder, toggle to show/hide</p>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-xl hover:bg-[#EEF1EC] transition-colors text-[#7A8580]"
          >
            <XMarkIcon className="w-5 h-5" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-6">
          <DndContext
            sensors={sensors}
            collisionDetection={closestCenter}
            onDragEnd={handleDragEnd}
          >
            <SortableContext items={widgetOrder} strategy={verticalListSortingStrategy}>
              <div className="space-y-2">
                {widgetOrder.map(id => (
                  <SortableItem
                    key={id}
                    id={id}
                    visible={widgetVisibility[id]}
                    onToggle={onToggleVisibility}
                  />
                ))}
              </div>
            </SortableContext>
          </DndContext>
        </div>

        <div className="p-6 border-t border-[#EEF1EC] flex gap-3">
          <button
            onClick={onReset}
            className="flex-1 px-4 py-2.5 text-sm font-medium text-[#7A8580] bg-[#F5F7F4] rounded-xl hover:bg-[#EEF1EC] transition-colors"
          >
            Reset to Default
          </button>
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2.5 text-sm font-medium text-white bg-[#5B8A72] rounded-xl hover:bg-[#4A7A62] transition-colors"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  )
}
