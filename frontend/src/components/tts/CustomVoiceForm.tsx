import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import * as z from 'zod'
import { useEffect, useState, forwardRef, useImperativeHandle, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue, SelectGroup, SelectLabel } from '@/components/ui/select'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { Globe2, User, Type, Sparkles, Play, Settings, Settings2, Trash2, Loader2 } from 'lucide-react'
import { toast } from 'sonner'
import { IconLabel } from '@/components/IconLabel'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { ttsApi, jobApi, voiceDesignApi } from '@/lib/api'
import { useJobPolling } from '@/hooks/useJobPolling'
import { useHistoryContext } from '@/contexts/HistoryContext'
import { useUserPreferences } from '@/contexts/UserPreferencesContext'
import { LoadingState } from '@/components/LoadingState'
import { AudioPlayer } from '@/components/AudioPlayer'
import { PresetSelector } from '@/components/PresetSelector'
import type { Language, UnifiedSpeakerItem } from '@/types/tts'

type FormData = {
  text: string
  language: string
  speaker: string
  instruct?: string
  max_new_tokens?: number
  temperature?: number
  top_k?: number
  top_p?: number
  repetition_penalty?: number
}

export interface CustomVoiceFormHandle {
  loadParams: (params: any) => void
}

const CustomVoiceForm = forwardRef<CustomVoiceFormHandle>((_props, ref) => {
  const { t } = useTranslation('tts')
  const { t: tCommon } = useTranslation('common')
  const { t: tErrors } = useTranslation('errors')
  const { t: tConstants } = useTranslation('constants')

  const PRESET_INSTRUCTS = useMemo(() => tConstants('presetInstructs', { returnObjects: true }) as Array<{ label: string; instruct: string; text: string }>, [tConstants])

  const formSchema = z.object({
    text: z.string().min(1, tErrors('validation.required', { field: tErrors('fieldNames.text') })).max(5000, tErrors('validation.maxLength', { field: tErrors('fieldNames.text'), max: 5000 })),
    language: z.string().min(1, tErrors('validation.required', { field: tErrors('fieldNames.language') })),
    speaker: z.string().min(1, tErrors('validation.required', { field: tErrors('fieldNames.speaker') })),
    instruct: z.string().optional(),
    max_new_tokens: z.number().min(1).max(10000).optional(),
    temperature: z.number().min(0).max(2).optional(),
    top_k: z.number().min(1).max(100).optional(),
    top_p: z.number().min(0).max(1).optional(),
    repetition_penalty: z.number().min(0).max(2).optional(),
  })
  const [languages, setLanguages] = useState<Language[]>([])
  const [unifiedSpeakers, setUnifiedSpeakers] = useState<UnifiedSpeakerItem[]>([])
  const [selectedSpeakerId, setSelectedSpeakerId] = useState<string>('')
  const [isLoading, setIsLoading] = useState(false)
  const [advancedOpen, setAdvancedOpen] = useState(false)
  const [manageVoicesOpen, setManageVoicesOpen] = useState(false)
  const [isDeleting, setIsDeleting] = useState<number | null>(null)
  const [tempAdvancedParams, setTempAdvancedParams] = useState({
    max_new_tokens: 2048,
    temperature: 0.9,
    top_k: 50,
    top_p: 1.0,
    repetition_penalty: 1.05
  })

  const { currentJob, isPolling, isCompleted, startPolling, elapsedTime } = useJobPolling()
  const { refresh } = useHistoryContext()
  const { preferences } = useUserPreferences()

  const selectedSpeaker = useMemo(() =>
    unifiedSpeakers.find(s => s.id === selectedSpeakerId),
    [unifiedSpeakers, selectedSpeakerId]
  )

  const isInstructDisabled = selectedSpeaker?.source === 'saved-design' || selectedSpeaker?.id?.startsWith('clone')

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
  } = useForm<FormData>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      text: '',
      language: 'Auto',
      speaker: '',
      instruct: '',
      max_new_tokens: 2048,
      temperature: 0.9,
      top_k: 50,
      top_p: 1.0,
      repetition_penalty: 1.05,
    },
  })

  useImperativeHandle(ref, () => ({
    loadParams: (params: any) => {
      setValue('text', params.text || '')
      setValue('language', params.language || 'Auto')
      setValue('speaker', params.speaker || '')

      if (params.speaker) {
        const item = unifiedSpeakers.find(s =>
          s.source === 'builtin' && s.id === params.speaker
        )
        if (item) {
          setSelectedSpeakerId(item.id)
        }
      }

      setValue('instruct', params.instruct || '')
      setValue('max_new_tokens', params.max_new_tokens || 2048)
      setValue('temperature', params.temperature || 0.9)
      setValue('top_k', params.top_k || 50)
      setValue('top_p', params.top_p || 1.0)
      setValue('repetition_penalty', params.repetition_penalty || 1.05)
    }
  }))

  useEffect(() => {
    const fetchData = async () => {
      try {
        const backend = 'aliyun'
        const [langs, builtinSpeakers, savedDesigns] = await Promise.all([
          ttsApi.getLanguages(),
          ttsApi.getSpeakers(backend),
          voiceDesignApi.list(backend)
        ])

        const designItems: UnifiedSpeakerItem[] = savedDesigns.designs.map(d => ({
          id: `design-${d.id}`,
          displayName: `${d.name}`,
          description: d.instruct.substring(0, 60) + (d.instruct.length > 60 ? '...' : ''),
          source: 'saved-design',
          designId: d.id,
          instruct: d.instruct,
          backendType: d.backend_type
        }))

        const builtinItems: UnifiedSpeakerItem[] = builtinSpeakers.map(s => ({
          id: s.name,
          displayName: s.name,
          description: s.description,
          source: 'builtin'
        }))

        setLanguages(langs)
        setUnifiedSpeakers([...designItems, ...builtinItems])
      } catch (error) {
        toast.error(t('loadDataFailed'))
      }
    }
    fetchData()
  }, [preferences?.default_backend, t])

  const handleDeleteVoice = async (designId: number) => {
    try {
      setIsDeleting(designId)
      await voiceDesignApi.delete(designId)
      toast.success(t('voiceDeleted', '音色已删除'))

      // Remove from selected if we deleted the currently selected voice
      if (selectedSpeakerId === `design-${designId}`) {
        setSelectedSpeakerId('')
        setValue('speaker', '')
        setValue('instruct', '')
      }

      // Refresh the list
      setUnifiedSpeakers(prev => prev.filter(s => s.designId !== designId))

      try {
        await refresh()
      } catch { }
    } catch (error: any) {
      toast.error(error.message || t('voiceDeleteFailed', '删除音色失败'))
    } finally {
      setIsDeleting(null)
    }
  }

  useEffect(() => {
    if (selectedSpeaker?.source === 'saved-design' && selectedSpeaker.instruct) {
      setValue('instruct', selectedSpeaker.instruct)
    }
  }, [selectedSpeakerId, selectedSpeaker, setValue])


  const onSubmit = async (data: FormData) => {
    setIsLoading(true)
    try {
      const selectedItem = unifiedSpeakers.find(s => s.id === selectedSpeakerId)

      let result
      if (selectedItem?.source === 'saved-design') {
        result = await ttsApi.createVoiceDesignJob({
          text: data.text,
          language: data.language,
          saved_design_id: selectedItem.designId,
          max_new_tokens: data.max_new_tokens ?? 2048,
          temperature: data.temperature ?? 0.9,
        })
      } else {
        result = await ttsApi.createCustomVoiceJob({
          text: data.text,
          language: data.language,
          speaker: data.speaker,
          instruct: data.instruct,
          max_new_tokens: data.max_new_tokens ?? 2048,
          temperature: data.temperature ?? 0.9,
        })
      }

      toast.success(t('taskCreated'))
      startPolling(result.job_id)
      try {
        await refresh()
      } catch { }
    } catch (error) {
      toast.error(t('taskCreateFailed'))
    } finally {
      setIsLoading(false)
    }
  }

  const memoizedAudioUrl = useMemo(() => {
    if (!currentJob) return ''
    return jobApi.getAudioUrl(currentJob.id, currentJob.audio_url)
  }, [currentJob?.id, currentJob?.audio_url])

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-2">
      <div className="space-y-0.5">
        <IconLabel icon={Globe2} tooltip={t('languageLabel')} required />
        <Select
          value={watch('language')}
          onValueChange={(value: string) => setValue('language', value)}
        >
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {languages.map((lang) => (
              <SelectItem key={lang.code} value={lang.code}>
                {tConstants(`languages.${lang.code}`, { defaultValue: lang.name })}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {errors.language && (
          <p className="text-sm text-destructive">{errors.language.message}</p>
        )}
      </div>

      <div className="space-y-0.5">
        <div className="flex items-center justify-between">
          <IconLabel icon={User} tooltip={t('speakerLabel')} required />
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="h-6 px-2 text-xs"
            onClick={() => setManageVoicesOpen(true)}
          >
            <Settings2 className="w-3 h-3 mr-1" />
            {t('manageVoices', '管理音色')}
          </Button>
        </div>
        <Select
          value={selectedSpeakerId}
          onValueChange={(value: string) => {
            const newSpeaker = unifiedSpeakers.find(s => s.id === value)
            const previousSource = selectedSpeaker?.source

            if (newSpeaker) {
              setSelectedSpeakerId(value)
              setValue('speaker', newSpeaker.id)

              if ((newSpeaker.source === 'builtin' || newSpeaker.id.startsWith('clone')) && previousSource === 'saved-design') {
                setValue('instruct', '')
              }
            }
          }}
        >
          <SelectTrigger>
            <SelectValue placeholder={t('speakerPlaceholder')}>
              {selectedSpeakerId && (() => {
                const item = unifiedSpeakers.find(s => s.id === selectedSpeakerId)
                if (!item) return null
                if (item.source === 'saved-design') {
                  return item.displayName
                }
                return `${item.displayName} - ${item.description}`
              })()}
            </SelectValue>
          </SelectTrigger>
          <SelectContent>
            {unifiedSpeakers.filter(s => s.source === 'saved-design').length > 0 && (
              <SelectGroup>
                <SelectLabel className="text-xs text-muted-foreground">{t('myVoiceDesigns')}</SelectLabel>
                {unifiedSpeakers
                  .filter(s => s.source === 'saved-design')
                  .map(item => (
                    <SelectItem key={item.id} value={item.id}>
                      <div className="flex flex-col">
                        <span className="font-medium">{item.displayName}</span>
                        <span className="text-xs text-muted-foreground">{item.description}</span>
                      </div>
                    </SelectItem>
                  ))}
              </SelectGroup>
            )}

            <SelectGroup>
              <SelectLabel className="text-xs text-muted-foreground">{t('builtinSpeakers')}</SelectLabel>
              {unifiedSpeakers
                .filter(s => s.source === 'builtin')
                .map(item => (
                  <SelectItem key={item.id} value={item.id}>
                    {item.displayName} - {item.description}
                  </SelectItem>
                ))}
            </SelectGroup>
          </SelectContent>
        </Select>
        {errors.speaker && (
          <p className="text-sm text-destructive">{errors.speaker.message}</p>
        )}
      </div>

      <div className="space-y-0.5">
        <IconLabel icon={Type} tooltip={t('textLabel')} required />
        <Textarea
          {...register('text')}
          placeholder={t('textPlaceholder')}
          className="min-h-[40px] md:min-h-[60px] relative focus:z-10"
        />
        {errors.text && (
          <p className="text-sm text-destructive">{errors.text.message}</p>
        )}
      </div>

      <div className="space-y-0.5">
        <IconLabel icon={Sparkles} tooltip={t('instructLabel')} />
        <Textarea
          {...register('instruct')}
          placeholder={isInstructDisabled
            ? t('instructPlaceholderDesign')
            : t('instructPlaceholderDefault')
          }
          className="min-h-[40px] md:min-h-[60px] relative focus:z-10"
          disabled={isInstructDisabled}
        />
        {!isInstructDisabled && (
          <PresetSelector
            presets={PRESET_INSTRUCTS}
            onSelect={(preset) => {
              setValue('instruct', preset.instruct)
              if (preset.text) {
                setValue('text', preset.text)
              }
            }}
          />
        )}
        {errors.instruct && (
          <p className="text-sm text-destructive">{errors.instruct.message}</p>
        )}
      </div>

      <Dialog open={advancedOpen} onOpenChange={(open) => {
        if (open) {
          setTempAdvancedParams({
            max_new_tokens: watch('max_new_tokens') || 2048,
            temperature: watch('temperature') || 0.9,
            top_k: watch('top_k') || 50,
            top_p: watch('top_p') || 1.0,
            repetition_penalty: watch('repetition_penalty') || 1.05
          })
        }
        setAdvancedOpen(open)
      }}>
        <DialogTrigger asChild>
          <Button type="button" variant="outline" className="w-full">
            <Settings className="mr-2 h-4 w-4" />
            {t('advancedOptions')}
          </Button>
        </DialogTrigger>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>{t('advancedOptionsTitle')}</DialogTitle>
            <DialogDescription>{t('advancedOptionsDescription')}</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="dialog-max_new_tokens">
                {t('advancedParams.maxNewTokens.label')}
              </Label>
              <Input
                id="dialog-max_new_tokens"
                type="number"
                min={1}
                max={10000}
                value={tempAdvancedParams.max_new_tokens}
                onChange={(e) => setTempAdvancedParams({
                  ...tempAdvancedParams,
                  max_new_tokens: parseInt(e.target.value) || 2048
                })}
              />
              <p className="text-sm text-muted-foreground">
                {t('advancedParams.maxNewTokens.description')}
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="dialog-temperature">
                {t('advancedParams.temperature.label')}
              </Label>
              <Input
                id="dialog-temperature"
                type="number"
                min={0}
                max={2}
                step={0.1}
                value={tempAdvancedParams.temperature}
                onChange={(e) => setTempAdvancedParams({
                  ...tempAdvancedParams,
                  temperature: parseFloat(e.target.value) || 0.9
                })}
              />
              <p className="text-sm text-muted-foreground">
                {t('advancedParams.temperature.description')}
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="dialog-top_k">
                {t('advancedParams.topK.label')}
              </Label>
              <Input
                id="dialog-top_k"
                type="number"
                min={1}
                max={100}
                value={tempAdvancedParams.top_k}
                onChange={(e) => setTempAdvancedParams({
                  ...tempAdvancedParams,
                  top_k: parseInt(e.target.value) || 20
                })}
              />
              <p className="text-sm text-muted-foreground">
                {t('advancedParams.topK.description')}
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="dialog-top_p">
                {t('advancedParams.topP.label')}
              </Label>
              <Input
                id="dialog-top_p"
                type="number"
                min={0}
                max={1}
                step={0.1}
                value={tempAdvancedParams.top_p}
                onChange={(e) => setTempAdvancedParams({
                  ...tempAdvancedParams,
                  top_p: parseFloat(e.target.value) || 0.7
                })}
              />
              <p className="text-sm text-muted-foreground">
                {t('advancedParams.topP.description')}
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="dialog-repetition_penalty">
                {t('advancedParams.repetitionPenalty.label')}
              </Label>
              <Input
                id="dialog-repetition_penalty"
                type="number"
                min={0}
                max={2}
                step={0.01}
                value={tempAdvancedParams.repetition_penalty}
                onChange={(e) => setTempAdvancedParams({
                  ...tempAdvancedParams,
                  repetition_penalty: parseFloat(e.target.value) || 1.05
                })}
              />
              <p className="text-sm text-muted-foreground">
                {t('advancedParams.repetitionPenalty.description')}
              </p>
            </div>
          </div>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                setTempAdvancedParams({
                  max_new_tokens: watch('max_new_tokens') || 2048,
                  temperature: watch('temperature') || 0.3,
                  top_k: watch('top_k') || 20,
                  top_p: watch('top_p') || 0.7,
                  repetition_penalty: watch('repetition_penalty') || 1.05
                })
                setAdvancedOpen(false)
              }}
            >
              {tCommon('cancel')}
            </Button>
            <Button
              type="button"
              onClick={() => {
                setValue('max_new_tokens', tempAdvancedParams.max_new_tokens)
                setValue('temperature', tempAdvancedParams.temperature)
                setValue('top_k', tempAdvancedParams.top_k)
                setValue('top_p', tempAdvancedParams.top_p)
                setValue('repetition_penalty', tempAdvancedParams.repetition_penalty)
                setAdvancedOpen(false)
              }}
            >
              {tCommon('ok')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={manageVoicesOpen} onOpenChange={setManageVoicesOpen}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>{t('manageVoices', '管理音色')}</DialogTitle>
            <DialogDescription>
              {t('manageVoicesDesc', '您可以删除不再需要的自定义音色或克隆音色。注意：删除云端音色是不可逆的。')}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 max-h-[60vh] overflow-y-auto">
            {unifiedSpeakers.filter(s => s.source === 'saved-design').length === 0 ? (
              <p className="text-center text-muted-foreground py-8">{t('noSavedVoices', '暂无保存的音色')}</p>
            ) : (
              <div className="space-y-2">
                {unifiedSpeakers
                  .filter(s => s.source === 'saved-design')
                  .map(item => (
                    <div key={item.id} className="flex items-center justify-between p-3 border rounded-lg bg-card">
                      <div className="flex flex-col flex-1 min-w-0 pr-4">
                        <span className="font-medium truncate">{item.displayName}</span>
                        <span className="text-xs text-muted-foreground truncate">{item.description}</span>
                      </div>
                      <Button
                        type="button"
                        variant="destructive"
                        size="sm"
                        className="shrink-0"
                        disabled={isDeleting === item.designId}
                        onClick={() => item.designId && handleDeleteVoice(item.designId)}
                      >
                        {isDeleting === item.designId ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <Trash2 className="w-4 h-4" />
                        )}
                        <span className="sr-only">{t('delete')}</span>
                      </Button>
                    </div>
                  ))}
              </div>
            )}
          </div>
          <DialogFooter>
            <Button type="button" onClick={() => setManageVoicesOpen(false)}>
              {tCommon('close')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button type="submit" className="w-full" disabled={isLoading || isPolling}>
              <Play className="mr-2 h-4 w-4" />
              {isLoading ? t('creating') : t('generate')}
            </Button>
          </TooltipTrigger>
          <TooltipContent>
            <p>{t('generate')}</p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>

      {isPolling && <LoadingState elapsedTime={elapsedTime} />}

      {isCompleted && currentJob && (
        <div className="space-y-4 pt-4 border-t">
          <AudioPlayer
            audioUrl={memoizedAudioUrl}
            jobId={currentJob.id}
            text={currentJob.parameters?.text}
          />
        </div>
      )}
    </form>
  )
})

export default CustomVoiceForm
