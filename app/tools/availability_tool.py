import logging
from typing import Optional, List
from ..models.scheduling import FullAgenda, FilteredAgenda, AvailabilitySearchParams

logger = logging.getLogger(__name__)


class AvailabilityTool:

    def filter_availability(
        self, agenda: FullAgenda, params: AvailabilitySearchParams
    ) -> FilteredAgenda:

        try:
            logger.info(
                f"[AVAILABILITY] Filtrando: service={params.service_name or params.service_id}"
            )

            service_id = self._resolve_service_id(agenda, params)

            if not service_id:
                return FilteredAgenda(options=[])

            service_info = agenda.services[service_id]

            professionals = self._find_professionals_for_service(
                agenda, service_id, params.professional_id, params.professional_name
            )

            options = []

            for prof_id in professionals:
                prof_info = agenda.professionals[prof_id]

                if service_id not in agenda.availability.get(prof_id, {}):
                    continue

                service_availability = agenda.availability[prof_id][service_id]

                dates_to_check = self._get_dates_to_check(
                    service_availability.keys(), params.date
                )

                for check_date in dates_to_check[:3]:
                    if check_date not in service_availability:
                        continue

                    slots = service_availability[check_date]

                    if params.time_preference:
                        slots = self._filter_by_time_preference(
                            slots, params.time_preference
                        )

                    if slots:
                        options.append(
                            {
                                "professional": prof_info.name,
                                "professional_id": prof_id,
                                "date": check_date,
                                "slots": slots[:5],
                            }
                        )

                    if len(options) >= params.max_results:
                        break

                if len(options) >= params.max_results:
                    break

            filtered = FilteredAgenda(
                service_id=service_id,
                service_name=service_info.name,
                price=service_info.price,
                duration=service_info.duration,
                options=options,
            )

            logger.info(f"[AVAILABILITY] Encontradas {len(options)} opções")
            return filtered

        except Exception as e:
            logger.error(f"[AVAILABILITY] Erro ao filtrar: {e}", exc_info=True)
            return FilteredAgenda(options=[])

    def _resolve_service_id(
        self, agenda: FullAgenda, params: AvailabilitySearchParams
    ) -> Optional[str]:
        """Resolve service_id a partir de nome ou ID"""
        if params.service_id:
            return params.service_id

        if params.service_name:
            search_term = params.service_name.lower()
            for service_id, service_info in agenda.services.items():
                if search_term in service_info.name.lower():
                    return service_id

        return None

    def _find_professionals_for_service(
        self,
        agenda: FullAgenda,
        service_id: str,
        professional_id: Optional[str] = None,
        professional_name: Optional[str] = None,
    ) -> List[str]:
        """Encontra profissionais que oferecem o serviço"""
        if professional_id:
            return [professional_id]

        professionals = []

        for prof_id, prof_info in agenda.professionals.items():
            if service_id in prof_info.services:
                if professional_name:
                    if professional_name.lower() in prof_info.name.lower():
                        professionals.append(prof_id)
                else:
                    professionals.append(prof_id)

        return professionals

    def _get_dates_to_check(
        self, available_dates: List[str], target_date: Optional[str] = None
    ) -> List[str]:

        dates = sorted(available_dates)

        if target_date and target_date in dates:
            dates.remove(target_date)
            dates.insert(0, target_date)

        return dates

    def _filter_by_time_preference(
        self, slots: List[str], preference: str
    ) -> List[str]:
        """Filtra slots por preferência de horário"""
        if preference == "morning":
            return [s for s in slots if s < "12:00"]
        elif preference == "afternoon":
            return [s for s in slots if "12:00" <= s < "18:00"]
        elif preference == "evening":
            return [s for s in slots if s >= "18:00"]
        return slots

    def get_next_available_slot(
        self, agenda: FullAgenda, service_id: str, professional_id: Optional[str] = None
    ) -> Optional[dict]:

        params = AvailabilitySearchParams(
            service_id=service_id, professional_id=professional_id, max_results=1
        )

        filtered = self.filter_availability(agenda, params)

        if filtered.options:
            option = filtered.options[0]
            return {
                "professional_id": option["professional_id"],
                "professional": option["professional"],
                "service_id": service_id,
                "service": filtered.service_name,
                "date": option["date"],
                "time": option["slots"][0],
                "price": filtered.price,
            }

        return None

    def format_for_llm(self, filtered: FilteredAgenda) -> str:

        if not filtered.options:
            return "Nenhum horário disponível para este serviço no momento."

        text = f"Serviço: {filtered.service_name}\n"
        text += f"Duração: {filtered.duration}min | Valor: R$ {filtered.price:.2f}\n\n"
        text += "Opções disponíveis:\n\n"

        for i, opt in enumerate(filtered.options, 1):
            text += f"Opção {i}:\n"
            text += f"  Profissional: {opt['professional']}\n"
            text += f"  Data: {opt['date']}\n"
            text += f"  Horários: {', '.join(opt['slots'])}\n\n"

        return text


availability_tool = AvailabilityTool()
