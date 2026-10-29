// Presentation only: the shared C# campaign view determines descent eligibility.
const escape = value => String(value ?? '').replace(/[&<>"']/g,
  c => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[c]));
const title = label => String(label ?? '').split(' / ')[0];

export function renderDescentReview(view, {portrait}) {
  const campaign = view.generatedCampaign;
  if (!campaign?.canConfirmDescent) return '';
  const finishing = campaign.floorNumber === campaign.totalFloors;
  const destination = finishing ? 'Expedition complete' : title(campaign.nextFloorLabel);
  const party = view.roster.filter(member => member.selected);

  return `<dialog id="descent-dialog" class="field-dialog" aria-labelledby="descent-title">
    <div class="dialog-head">
      <h2 id="descent-title">${finishing ? 'Leave the expedition?' : 'Ready to descend?'}</h2>
      <button id="close-descent" aria-label="Keep exploring">×</button>
    </div>
    <div class="modal-body">
      <div class="descent-destination">
        <small>DEPTH ${campaign.floorNumber} OF ${campaign.totalFloors} CLEARED</small>
        <h3>${escape(destination)}</h3>
        <p>${finishing
          ? 'Your completed route and party will remain in this save.'
          : 'Descent is one-way. Your party, supplies, equipment and learned skills carry forward.'}</p>
      </div>
      <p class="descent-resource-note">Health and Mana stay as they are. Rest in the safe room first if you need to recover.</p>
      <div class="descent-party" aria-label="Party resources carried forward">
        ${party.map(member => `<div class="descent-crawler">
          ${portrait(member)}
          <div><strong>${escape(member.label)}</strong>
            <span>HP ${member.hp}/${member.maxHp}</span>
            <span>Mana ${member.energy}/${member.maxEnergy}</span>
          </div>
        </div>`).join('')}
      </div>
    </div>
    <div class="modal-actions">
      <button id="cancel-descent">Keep exploring</button>
      <button id="confirm-descent" class="primary">${finishing ? 'Finish expedition' : 'Descend'}</button>
    </div>
  </dialog>`;
}

export function renderCampaignEnding(view, {survivors, log}) {
  const campaign = view.generatedCampaign;
  return `<section class="outcome-layout" aria-labelledby="screen-title">
    <div class="center-outcome">
      <div class="trophy" aria-hidden="true">♜</div>
      <h2 id="screen-title">Expedition complete.</h2>
      <p>${escape(campaign.label)} · All ${campaign.totalFloors} depths cleared.</p>
      <p>Your party and progress are saved. Export this run to keep it before starting another expedition.</p>
      <div class="tags" style="justify-content:center">
        <span class="tag gold">${campaign.completedFloors} DEPTHS COMPLETE</span>
        <span class="tag">${view.xp} XP EARNED</span>
      </div>
      <div class="button-row">
        <button id="ending-export" class="primary">Export completed run</button>
        <button data-generated-adventure>New expedition</button>
      </div>
    </div>
    ${survivors()}${log()}
  </section>`;
}
