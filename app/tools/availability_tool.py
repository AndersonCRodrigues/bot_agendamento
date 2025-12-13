import logging
from datetime import datetime
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
            now = datetime.now()
            current_date = now.strftime("%Y-%m-%d")
            current_time = now.strftime("%H:%M")

            logger.info(
                f"[AVAILABILITY] Filtrando horários a partir de {current_date} {current_time}"
            )

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

                    if check_date < current_date:
                        logger.debug(
                            f"[AVAILABILITY] Ignorando data passada: {check_date}"
                        )
                        continue

                    slots = service_availability[check_date]

                    if check_date == current_date:
                        slots = [slot for slot in slots if slot > current_time]
                        if not slots:
                            logger.debug(
                                f"[AVAILABILITY] Sem horários futuros para hoje"
                            )
                            continue

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

            logger.info(
                f"[AVAILABILITY] Encontradas {len(options)} opções (somente futuras)"
            )
            return filtered

        except Exception as e:
            logger.error(f"[AVAILABILITY] Erro ao filtrar: {e}", exc_info=True)
            return FilteredAgenda(options=[])


availability_tool = AvailabilityTool()
